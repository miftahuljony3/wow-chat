"""
Webhook Gateway — WhatsApp, Facebook Messenger, Telegram, Discord.

Design: receive → verify → push to Celery → return 200 immediately.
Meta requires HTTP 200 within 20 s or it retries.
Telegram requires HTTP 200 or it retries every few seconds.
Discord requires HTTP 200 (and {type:1} for PING) within 3 s.
"""

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .tasks import (
    process_whatsapp_payload,
    process_messenger_payload,
    process_feed_event,
    process_telegram_payload,
    process_discord_payload,
)

logger = logging.getLogger(__name__)


# ── Signature helpers ─────────────────────────────────────────────────────────

def _verify_meta_signature(request, app_secret: str) -> bool:
    """Validate X-Hub-Signature-256 header (WhatsApp / Messenger / Instagram)."""
    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not signature_header.startswith("sha256="):
        return False
    received = signature_header[7:]
    expected = hmac.new(
        app_secret.encode(), request.body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(received, expected)


def _verify_discord_signature(public_key_hex: str, timestamp: str, body: bytes, sig_hex: str) -> bool:
    """Verify Discord Ed25519 interaction signature using the cryptography library."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        pub.verify(bytes.fromhex(sig_hex), timestamp.encode() + body)
        return True
    except Exception:
        return False


# ── WhatsApp ──────────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class WhatsAppWebhookView(View):
    """GET = hub challenge; POST = signed message events."""

    def get(self, request):
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
            logger.info("WhatsApp webhook verified.")
            return HttpResponse(challenge, content_type="text/plain")

        logger.warning("WhatsApp webhook verification failed.")
        return HttpResponse(status=403)

    def post(self, request):
        if settings.WHATSAPP_APP_SECRET:
            if not _verify_meta_signature(request, settings.WHATSAPP_APP_SECRET):
                logger.warning("WhatsApp webhook: invalid signature.")
                return HttpResponse(status=401)

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse(status=400)

        process_whatsapp_payload.apply_async(args=[payload], queue="webhooks", countdown=0)
        return HttpResponse(status=200)


# ── Facebook Messenger ────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class MessengerWebhookView(View):
    """Facebook Messenger webhook (same Meta hub pattern)."""

    VERIFY_TOKEN = "messenger_verify_token"

    def get(self, request):
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == self.VERIFY_TOKEN:
            return HttpResponse(challenge, content_type="text/plain")
        return HttpResponse(status=403)

    def post(self, request):
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse(status=400)

        for entry in payload.get("entry", []):
            page_id = entry.get("id", "")

            # ── Messenger messages ──────────────────────────────────────────
            if entry.get("messaging"):
                process_messenger_payload.apply_async(
                    args=[{"entry": [entry]}], queue="webhooks", countdown=0
                )

            # ── Page feed: posts, comments, reactions ───────────────────────
            for change in entry.get("changes", []):
                if change.get("field") == "feed":
                    value = change.get("value", {})
                    item = value.get("item", "")
                    verb = value.get("verb", "")
                    # Only process new comments (not edits, likes, shares)
                    if item == "comment" and verb == "add":
                        process_feed_event.apply_async(
                            args=[value, page_id], queue="webhooks", countdown=0
                        )

        return HttpResponse(status=200)


# ── Telegram ──────────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class TelegramWebhookView(View):
    """
    POST-only — Telegram Bot API Update objects.

    Telegram authenticates via X-Telegram-Bot-Api-Secret-Token header.
    The secret_token is set when calling setWebhook and must match the
    verify_token stored on the ChannelIntegration.

    No GET challenge: Telegram registration is done via Bot API setWebhook.
    """

    def post(self, request):
        # secret_token passed by Telegram matches the verify_token on the integration
        secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse(status=400)

        if not payload.get("update_id"):
            # Not a valid Telegram Update
            return HttpResponse(status=400)

        process_telegram_payload.apply_async(
            args=[payload, secret_token],
            queue="webhooks",
            countdown=0,
        )
        # Must return 200 immediately so Telegram stops retrying
        return HttpResponse(status=200)


# ── Discord ───────────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class DiscordWebhookView(View):
    """
    Discord Interactions Endpoint.

    Discord signs every request with Ed25519. The application's Public Key
    (from Discord Developer Portal → General Information) must be stored in
    the ChannelIntegration.app_secret field.

    Type 1 = PING (must respond synchronously with {type: 1}).
    Type 2 = APPLICATION_COMMAND (slash command).
    Type 3 = MESSAGE_COMPONENT (button/select).

    Note: regular channel messages (not slash commands) require a bot
    connected to the Gateway WebSocket, not an Interactions Endpoint.
    """

    def post(self, request):
        signature = request.headers.get("X-Signature-Ed25519", "")
        timestamp = request.headers.get("X-Signature-Timestamp", "")

        if not signature or not timestamp:
            return HttpResponse(status=401)

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse(status=400)

        interaction_type = payload.get("type")
        guild_id = payload.get("guild_id", "")

        # ── PING (type 1) ── must verify + respond synchronously ──────────────
        if interaction_type == 1:
            verified = self._verify_ping(request.body, timestamp, signature, guild_id)
            if not verified:
                logger.warning("Discord PING signature verification failed (guild=%s).", guild_id)
                return HttpResponse(status=401)
            return JsonResponse({"type": 1})

        # ── Interaction (type 2/3) ── verify then offload to Celery ──────────
        if not self._verify_with_guild(request.body, timestamp, signature, guild_id):
            logger.warning("Discord interaction signature invalid (guild=%s).", guild_id)
            return HttpResponse(status=401)

        process_discord_payload.apply_async(
            args=[payload, guild_id],
            queue="webhooks",
            countdown=0,
        )
        # Deferred response — bot will send follow-up via REST API
        return JsonResponse({"type": 5})

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _verify_ping(body: bytes, timestamp: str, signature: str, guild_id: str) -> bool:
        """For PING: try all active Discord integrations' public keys."""
        from apps.channels_integration.models import ChannelIntegration

        integrations = ChannelIntegration.objects.filter(
            platform=ChannelIntegration.Platform.DISCORD,
            is_active=True,
        ).exclude(app_secret="")

        for intg in integrations:
            if _verify_discord_signature(intg.app_secret, timestamp, body, signature):
                return True

        # Fallback: global public key in settings (optional)
        global_key = getattr(settings, "DISCORD_PUBLIC_KEY", "")
        if global_key:
            return _verify_discord_signature(global_key, timestamp, body, signature)

        return False

    @staticmethod
    def _verify_with_guild(body: bytes, timestamp: str, signature: str, guild_id: str) -> bool:
        """For non-PING: look up by guild_id first, then try all."""
        from apps.channels_integration.models import ChannelIntegration

        # Try the specific integration by guild_id
        if guild_id:
            try:
                intg = ChannelIntegration.objects.get(
                    platform=ChannelIntegration.Platform.DISCORD,
                    discord_guild_id=guild_id,
                    is_active=True,
                )
                return _verify_discord_signature(intg.app_secret, timestamp, body, signature)
            except ChannelIntegration.DoesNotExist:
                pass

        # Fallback: try all (covers DMs / global commands with no guild_id)
        from apps.channels_integration.models import ChannelIntegration as CI
        for intg in CI.objects.filter(platform=CI.Platform.DISCORD, is_active=True).exclude(app_secret=""):
            if _verify_discord_signature(intg.app_secret, timestamp, body, signature):
                return True

        global_key = getattr(settings, "DISCORD_PUBLIC_KEY", "")
        return bool(global_key and _verify_discord_signature(global_key, timestamp, body, signature))
