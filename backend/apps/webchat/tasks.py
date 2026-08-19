"""
Celery tasks for the web chat widget.
"""

import logging
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.inbox.mongo import (
    ConversationRepository,
    MessageRepository,
    build_message,
    build_conversation,
)

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


@shared_task(queue="webhooks", name="webchat.process_webchat_message")
def process_webchat_message(
    *, session_id: str, integration_id: str, workspace_id: str,
    content: str, sender_name: str = "Visitor",
):
    conv_repo = ConversationRepository()
    msg_repo = MessageRepository()

    contact_id = f"webchat_{session_id}"

    conversation = conv_repo.get_or_create(
        workspace_id=workspace_id,
        platform="web_chat",
        contact_id=contact_id,
        contact_name=sender_name,
        channel_integration_id=integration_id,
    )
    conversation_id = conversation["_id"]

    message = build_message(
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        platform="web_chat",
        direction="inbound",
        sender_id=contact_id,
        sender_name=sender_name,
        message_type="text",
        content=content,
        raw_payload={"session_id": session_id},
    )
    msg_repo.insert(message)
    conv_repo.update_last_message(conversation_id, content, increment_unread=True)

    # Broadcast inbound message to agent inbox dashboard
    async_to_sync(channel_layer.group_send)(
        f"inbox_{workspace_id}",
        {
            "type": "new_message",
            "data": {
                "message": {**message, "id": message["_id"]},
                "conversation": {**conversation, "id": conversation["_id"]},
            },
        },
    )

    # Trigger AI auto-reply if bot is active
    if conversation.get("bot_active"):
        from apps.ai_agent.tasks import generate_ai_response
        generate_ai_response.delay(
            conversation_id=conversation_id,
            message_id=message["_id"],
            integration_id=integration_id,
        )
