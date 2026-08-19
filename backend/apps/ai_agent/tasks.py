"""
Celery tasks for AI auto-response generation and human handoff.
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
from .services import WhatsAppService, TelegramService, DiscordService, LLMService

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()

HANDOFF_TRIGGERS = ["human", "agent", "speak to someone", "real person", "help me"]


def _check_handoff_trigger(text: str, custom_keywords: list) -> bool:
    text_lower = text.lower()
    keywords = HANDOFF_TRIGGERS + [k.lower() for k in custom_keywords]
    return any(kw in text_lower for kw in keywords)


def _get_platform_service(integration: ChannelIntegration, platform: str):
    """Return the appropriate messaging service for the given platform."""
    if platform in ("whatsapp", "messenger", "instagram"):
        return WhatsAppService(integration.phone_number_id, integration.access_token)
    if platform == "telegram":
        return TelegramService(integration.telegram_bot_token)
    if platform == "discord":
        return DiscordService(integration.discord_bot_token, integration.discord_channel_id)
    return None


def _extract_platform_msg_id(resp: dict, platform: str) -> str:
    if platform in ("whatsapp", "messenger", "instagram"):
        return resp.get("messages", [{}])[0].get("id", "")
    if platform == "telegram":
        return str(resp.get("result", {}).get("message_id", ""))
    if platform == "discord":
        return resp.get("id", "")
    return ""


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=3,
    queue="ai_responses",
    name="ai_agent.generate_ai_response",
)
def generate_ai_response(self, conversation_id: str, message_id: str, integration_id: str):
    """
    1. Fetch conversation context from MongoDB
    2. Check for human-handoff triggers
    3. Generate LLM response
    4. Send reply via the correct platform (WhatsApp / Telegram / Discord)
    5. Persist outbound message + broadcast to dashboard
    """
    try:
        conv_repo = ConversationRepository()
        msg_repo = MessageRepository()

        conversation = conv_repo.get_by_id(conversation_id)
        if not conversation:
            logger.warning("Conversation %s not found.", conversation_id)
            return

        if not conversation.get("bot_active"):
            logger.info("Bot inactive for conversation %s, skipping.", conversation_id)
            return

        integration = ChannelIntegration.objects.select_related("workspace").get(
            id=integration_id
        )
        platform = conversation.get("platform", "whatsapp")

        # Fetch last 10 messages for context
        history_docs = msg_repo.list_for_conversation(conversation_id, limit=10)
        history_docs.reverse()  # oldest first

        conversation_history = [
            {
                "role": "user" if m["direction"] == "inbound" else "assistant",
                "content": m["content"],
            }
            for m in history_docs
            if m["_id"] != message_id
        ]

        trigger_msg = next(
            (m for m in history_docs if m["_id"] == message_id), None
        )
        if not trigger_msg:
            return

        user_text = trigger_msg["content"]

        # Human handoff check
        if _check_handoff_trigger(user_text, integration.ai_handoff_keywords or []):
            conv_repo.set_bot_active(conversation_id, False)
            _broadcast_update(
                str(integration.workspace_id),
                conversation_id,
                {"bot_active": False, "reason": "handoff_triggered"},
            )
            handoff_msg = (
                "I'm connecting you with a human agent now. "
                "Please hold on for a moment."
            )
            _send_and_persist(
                integration=integration,
                conversation=conversation,
                workspace_id=str(integration.workspace_id),
                to=conversation["contact_id"],
                content=handoff_msg,
                platform=platform,
                conv_repo=conv_repo,
                msg_repo=msg_repo,
            )
            return

        # Generate AI response
        system_prompt = integration.ai_system_prompt.format(
            workspace=integration.workspace.name
        )
        llm = LLMService()
        reply_text = llm.generate_response(system_prompt, conversation_history, user_text)

        _send_and_persist(
            integration=integration,
            conversation=conversation,
            workspace_id=str(integration.workspace_id),
            to=conversation["contact_id"],
            content=reply_text,
            platform=platform,
            conv_repo=conv_repo,
            msg_repo=msg_repo,
        )

    except Exception as exc:
        logger.exception("AI response task failed: %s", exc)
        raise self.retry(exc=exc)


def _send_and_persist(
    *, integration, conversation, workspace_id, to, content, platform,
    conv_repo, msg_repo
):
    """Send outbound message via the correct platform API and save to MongoDB."""
    platform_msg_id = ""

    if platform == "web_chat":
        # Deliver directly to the visitor's WebSocket via channel layer
        session_id = conversation["contact_id"].removeprefix("webchat_")
        try:
            async_to_sync(channel_layer.group_send)(
                f"webchat_{session_id}",
                {
                    "type": "chat_message",
                    "data": {"type": "message", "direction": "outbound", "content": content, "sender": "bot"},
                },
            )
        except Exception as exc:
            logger.error("WebChat push failed for session %s: %s", session_id, exc)
    else:
        svc = _get_platform_service(integration, platform)
        if svc:
            try:
                resp = svc.send_text(to=to, body=content)
                platform_msg_id = _extract_platform_msg_id(resp, platform)
            except Exception as exc:
                logger.error("Failed to send %s message to %s: %s", platform, to, exc)
        else:
            logger.warning("No outbound service configured for platform=%s", platform)

    message = build_message(
        conversation_id=conversation["_id"],
        workspace_id=workspace_id,
        platform=platform,
        direction="outbound",
        sender_id="bot",
        sender_name="Wow Chat AI",
        message_type="text",
        content=content,
        raw_payload={},
        platform_message_id=platform_msg_id,
    )
    msg_repo.insert(message)
    conv_repo.update_last_message(conversation["_id"], content, increment_unread=False)

    group = f"inbox_{workspace_id}"
    payload = {
        "message": {**message, "id": message["_id"]},
        "conversation": {**conversation, "id": conversation["_id"]},
    }
    async_to_sync(channel_layer.group_send)(
        group, {"type": "new_message", "data": payload}
    )


def _broadcast_update(workspace_id: str, conversation_id: str, data: dict):
    group = f"inbox_{workspace_id}"
    async_to_sync(channel_layer.group_send)(
        group,
        {"type": "conversation_update", "data": {"conversation_id": conversation_id, **data}},
    )


@shared_task(queue="ai_responses", name="ai_agent.human_handoff")
def trigger_human_handoff(conversation_id: str, workspace_id: str):
    """Manually triggered by a human agent clicking 'Take Over'."""
    conv_repo = ConversationRepository()
    conv_repo.set_bot_active(conversation_id, False)
    _broadcast_update(workspace_id, conversation_id, {"bot_active": False, "reason": "manual"})
