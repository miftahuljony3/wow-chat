"""
External API service classes.

WhatsAppService  — sends messages via WhatsApp Cloud API
TelegramService  — sends messages via Telegram Bot API
DiscordService   — sends messages via Discord REST API
LLMService       — generates AI responses via Groq
"""

import logging
from typing import Optional

import httpx
from django.conf import settings
from groq import Groq

logger = logging.getLogger(__name__)

WHATSAPP_API_VERSION = "v19.0"
WHATSAPP_API_BASE = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"


class WhatsAppService:
    """Outbound WhatsApp Cloud API calls."""

    def __init__(self, phone_number_id: str, access_token: str):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self._base = f"{WHATSAPP_API_BASE}/{phone_number_id}/messages"
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def send_text(self, to: str, body: str) -> dict:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        }
        return self._post(payload)

    def send_template(self, to: str, template_name: str, language_code: str = "en_US") -> dict:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }
        return self._post(payload)

    def _post(self, payload: dict) -> dict:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(self._base, json=payload, headers=self._headers)
            resp.raise_for_status()
            return resp.json()


class TelegramService:
    """Outbound Telegram Bot API calls."""

    BASE = "https://api.telegram.org"

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self._base = f"{self.BASE}/bot{bot_token}"

    def send_text(self, to: str, body: str) -> dict:
        """Send a text message. `to` is the chat_id (user/group id as string)."""
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{self._base}/sendMessage",
                json={"chat_id": to, "text": body, "parse_mode": "HTML"},
            )
            resp.raise_for_status()
            return resp.json()

    def send_chat_action(self, to: str, action: str = "typing") -> dict:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(
                f"{self._base}/sendChatAction",
                json={"chat_id": to, "action": action},
            )
            return resp.json()

    def set_webhook(self, url: str, secret_token: str = "") -> dict:
        """Register the webhook URL with Telegram. Call once during setup."""
        with httpx.Client(timeout=10.0) as client:
            payload: dict = {"url": url}
            if secret_token:
                payload["secret_token"] = secret_token
            resp = client.post(f"{self._base}/setWebhook", json=payload)
            resp.raise_for_status()
            return resp.json()


class DiscordService:
    """Outbound Discord REST API calls (bot token auth)."""

    BASE = "https://discord.com/api/v10"

    def __init__(self, bot_token: str, default_channel_id: str = ""):
        self.bot_token = bot_token
        self.default_channel_id = default_channel_id
        self._headers = {
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json",
        }

    def send_text(self, to: str, body: str) -> dict:
        """
        Send a plain text message to a channel.
        `to` is the channel_id; falls back to default_channel_id if empty.
        """
        channel_id = to or self.default_channel_id
        if not channel_id:
            raise ValueError("No channel_id provided for Discord message.")
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{self.BASE}/channels/{channel_id}/messages",
                json={"content": body},
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    def respond_to_interaction(self, interaction_token: str, body: str) -> dict:
        """Reply to a Discord interaction (slash command) via follow-up message."""
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{self.BASE}/webhooks/{settings.DISCORD_APPLICATION_ID}/{interaction_token}",
                json={"content": body},
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()


class LLMService:
    """Wrapper around Groq chat completions (llama-3.3-70b-versatile by default)."""

    def __init__(self, model: Optional[str] = None):
        self._client = Groq(api_key=settings.GROQ_API_KEY)
        self._model = model or settings.GROQ_MODEL

    def generate_response(
        self,
        system_prompt: str,
        conversation_history: list[dict],
        user_message: str,
        max_tokens: int = 500,
    ) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history[-10:])
        messages.append({"role": "user", "content": user_message})

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            logger.exception("Groq LLM generation failed: %s", exc)
            return "I'm sorry, I'm having trouble responding right now. Please try again shortly."
