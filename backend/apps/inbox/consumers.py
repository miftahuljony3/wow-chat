"""
WebSocket consumer — one group per workspace.
Clients subscribe on connect and receive new_message / bot_status events.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer


class InboxConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.workspace_id = str(user.workspace_id)
        self.group_name = f"inbox_{self.workspace_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Clients can send ping / mark_read commands
        try:
            data = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            return

        if data.get("type") == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))

    # ── Group message handlers ────────────────────────────────────────────────

    async def new_message(self, event):
        """Broadcast a new incoming/outgoing message to all workspace clients."""
        await self.send(text_data=json.dumps({"type": "new_message", "data": event["data"]}))

    async def conversation_update(self, event):
        """Broadcast conversation-level changes (bot status, assignment)."""
        await self.send(
            text_data=json.dumps({"type": "conversation_update", "data": event["data"]})
        )
