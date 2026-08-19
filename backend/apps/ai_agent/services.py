"""
External API service classes.

WhatsAppService  — sends messages via WhatsApp Cloud API
LLMService       — generates AI responses via OpenAI
"""

import logging
from typing import Optional

import httpx
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

WHATSAPP_API_VERSION = "v19.0"
WHATSAPP_API_BASE = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"


class WhatsAppService:
    """Service for outbound WhatsApp Cloud API calls."""

    def __init__(self, phone_number_id: str, access_token: str):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self._base = f"{WHATSAPP_API_BASE}/{phone_number_id}/messages"
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def send_text(self, to: str, body: str) -> dict:
        """Send a plain text message. Returns the API response JSON."""
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


class LLMService:
    """Wrapper around OpenAI chat completions."""

    def __init__(self, model: Optional[str] = None):
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = model or settings.OPENAI_MODEL

    def generate_response(
        self,
        system_prompt: str,
        conversation_history: list[dict],
        user_message: str,
        max_tokens: int = 500,
    ) -> str:
        """
        Generate an AI response given the conversation context.
        conversation_history: list of {"role": "user"|"assistant", "content": str}
        """
        messages = [{"role": "system", "content": system_prompt}]
        # Include last 10 turns for context window efficiency
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
            logger.exception("LLM generation failed: %s", exc)
            return "I'm sorry, I'm having trouble responding right now. Please try again shortly."
