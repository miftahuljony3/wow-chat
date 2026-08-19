"""
WebSocket consumer for the embeddable web chat widget.

URL: ws/webchat/<session_id>/
No auth required — sessions are validated against a Redis key seeded by the
HTTP session-init endpoint. The UUID session_id acts as the bearer credential.
"""

import json
import logging

import redis.asyncio as aioredis
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

logger = logging.getLogger(__name__)


class WebChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.room = f"webchat_{self.session_id}"

        session = await self._get_session()
        if not session:
            await self.close(code=4004)
            return

        self.integration_id = session["integration_id"]
        self.workspace_id = session["workspace_id"]

        await self.channel_layer.group_add(self.room, self.channel_name)
        await self.accept()
        logger.info("WebChat connected: session=%s", self.session_id)

    async def disconnect(self, code):
        if hasattr(self, "room"):
            await self.channel_layer.group_discard(self.room, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            return

        if data.get("type") == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))
            return

        if data.get("type") == "message":
            content = (data.get("content") or "").strip()
            if not content:
                return

            from apps.webchat.tasks import process_webchat_message
            process_webchat_message.delay(
                session_id=self.session_id,
                integration_id=self.integration_id,
                workspace_id=self.workspace_id,
                content=content,
                sender_name=data.get("sender_name", "Visitor"),
            )

    # ── Channel layer handlers ─────────────────────────────────────────────────

    async def chat_message(self, event):
        """Push a message from the channel layer back to the browser widget."""
        await self.send(text_data=json.dumps(event["data"]))

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _get_session(self) -> dict | None:
        try:
            r = aioredis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
            raw = await r.get(f"webchat:{self.session_id}")
            await r.aclose()
            if raw:
                return json.loads(raw)
        except Exception as exc:
            logger.error("WebChat Redis lookup failed: %s", exc)
        return None
