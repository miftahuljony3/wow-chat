"""
Celery tasks for processing incoming webhook payloads.

Flow:
  raw payload → parse → upsert Conversation in Mongo
              → insert Message in Mongo
              → broadcast via Django Channels
              → trigger AI responder task (if bot_active)
"""

import logging
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.inbox.mongo import (
    ConversationRepository,
    MessageRepository,
    build_message,
)
from apps.channels_integration.models import ChannelIntegration

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


def _broadcast_new_message(workspace_id: str, message: dict, conversation: dict):
    """Push new_message event to all connected dashboard clients in the workspace."""
    group = f"inbox_{workspace_id}"
    payload = {
        "message": {**message, "id": message["_id"]},
        "conversation": {**conversation, "id": conversation["_id"]},
    }
    async_to_sync(channel_layer.group_send)(
        group,
        {"type": "new_message", "data": payload},
    )


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    queue="webhooks",
    name="webhooks.process_whatsapp_payload",
)
def process_whatsapp_payload(self, payload: dict):
    """
    Parse a WhatsApp Cloud API payload and persist to MongoDB.
    Supports text messages; extend message_type handling as needed.
    """
    try:
        entry = payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})

        messages = value.get("messages", [])
        if not messages:
            # Delivery receipts, status updates — skip
            return

        contacts = {c["wa_id"]: c.get("profile", {}).get("name", "Unknown")
                    for c in value.get("contacts", [])}
        metadata = value.get("metadata", {})
        phone_number_id = metadata.get("phone_number_id", "")

        # Look up the ChannelIntegration to get workspace
        try:
            integration = ChannelIntegration.objects.select_related("workspace").get(
                platform=ChannelIntegration.Platform.WHATSAPP,
                phone_number_id=phone_number_id,
                is_active=True,
            )
        except ChannelIntegration.DoesNotExist:
            logger.warning("No active WhatsApp integration for phone_number_id=%s", phone_number_id)
            return

        workspace_id = str(integration.workspace_id)
        conv_repo = ConversationRepository()
        msg_repo = MessageRepository()

        for raw_msg in messages:
            sender_id = raw_msg.get("from", "")
            sender_name = contacts.get(sender_id, sender_id)
            msg_type = raw_msg.get("type", "text")
            content = _extract_whatsapp_content(raw_msg, msg_type)

            conversation, _ = conv_repo.get_or_create(
                workspace_id=workspace_id,
                platform="whatsapp",
                contact_id=sender_id,
                contact_name=sender_name,
                channel_integration_id=str(integration.id),
            )

            message = build_message(
                conversation_id=conversation["_id"],
                workspace_id=workspace_id,
                platform="whatsapp",
                direction="inbound",
                sender_id=sender_id,
                sender_name=sender_name,
                message_type=msg_type,
                content=content,
                raw_payload=raw_msg,
                platform_message_id=raw_msg.get("id", ""),
            )
            msg_repo.insert(message)
            conv_repo.update_last_message(conversation["_id"], content)

            _broadcast_new_message(workspace_id, message, conversation)

            # Trigger AI responder if bot is active
            if conversation.get("bot_active") and integration.ai_enabled:
                from apps.ai_agent.tasks import generate_ai_response
                generate_ai_response.apply_async(
                    args=[conversation["_id"], message["_id"], str(integration.id)],
                    queue="ai_responses",
                )

    except Exception as exc:
        logger.exception("Error processing WhatsApp payload: %s", exc)
        raise self.retry(exc=exc)


def _extract_whatsapp_content(msg: dict, msg_type: str) -> str:
    """Extract text content from a WhatsApp message object."""
    if msg_type == "text":
        return msg.get("text", {}).get("body", "")
    if msg_type == "image":
        return msg.get("image", {}).get("caption", "[Image]")
    if msg_type == "audio":
        return "[Voice message]"
    if msg_type == "document":
        return msg.get("document", {}).get("filename", "[Document]")
    if msg_type == "location":
        loc = msg.get("location", {})
        return f"[Location: {loc.get('latitude')}, {loc.get('longitude')}]"
    return f"[{msg_type}]"


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    queue="webhooks",
    name="webhooks.process_messenger_payload",
)
def process_messenger_payload(self, payload: dict):
    """Parse Facebook Messenger payload — structure mirrors WhatsApp task."""
    try:
        for entry in payload.get("entry", []):
            for messaging in entry.get("messaging", []):
                msg = messaging.get("message", {})
                if not msg:
                    continue
                sender_id = messaging.get("sender", {}).get("id", "")
                content = msg.get("text", "[Attachment]")
                logger.info("Messenger message from %s: %s", sender_id, content[:50])
                # TODO: look up integration by page_id and persist (same pattern as WhatsApp)
    except Exception as exc:
        logger.exception("Error processing Messenger payload: %s", exc)
        raise self.retry(exc=exc)
