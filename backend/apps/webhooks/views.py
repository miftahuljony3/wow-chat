"""
Webhook Gateway — Meta (WhatsApp Cloud API + Facebook Messenger).

Design: receive → verify signature → push to Celery → return 200 immediately.
The 200 response must arrive within 20 s or Meta retries.
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

from .tasks import process_whatsapp_payload, process_messenger_payload

logger = logging.getLogger(__name__)


def _verify_meta_signature(request, app_secret: str) -> bool:
    """Validate X-Hub-Signature-256 header against raw body."""
    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not signature_header.startswith("sha256="):
        return False
    received = signature_header[7:]
    expected = hmac.new(
        app_secret.encode(), request.body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(received, expected)


@method_decorator(csrf_exempt, name="dispatch")
class WhatsAppWebhookView(View):
    """
    GET  — webhook verification challenge from Meta
    POST — incoming message events, signed with X-Hub-Signature-256
    """

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
        # Verify signature when app_secret is configured
        if settings.WHATSAPP_APP_SECRET:
            if not _verify_meta_signature(request, settings.WHATSAPP_APP_SECRET):
                logger.warning("WhatsApp webhook: invalid signature.")
                return HttpResponse(status=401)

        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse(status=400)

        # Immediately offload to Celery — do not block the response
        process_whatsapp_payload.apply_async(
            args=[payload],
            queue="webhooks",
            countdown=0,
        )

        # Meta requires HTTP 200 to acknowledge receipt
        return HttpResponse(status=200)


@method_decorator(csrf_exempt, name="dispatch")
class MessengerWebhookView(View):
    """Facebook Messenger webhook (same pattern as WhatsApp)."""

    VERIFY_TOKEN = "messenger_verify_token"  # configure per-integration later

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

        process_messenger_payload.apply_async(
            args=[payload],
            queue="webhooks",
            countdown=0,
        )
        return HttpResponse(status=200)
