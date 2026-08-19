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


def _trigger_ai(conversation: dict, message: dict, integration: ChannelIntegration):
    """Fire generate_ai_response if the bot is active for this conversation."""
    if conversation.get("bot_active") and integration.ai_enabled:
        from apps.ai_agent.tasks import generate_ai_response
        generate_ai_response.apply_async(
            args=[conversation["_id"], message["_id"], str(integration.id)],
            queue="ai_responses",
        )


# ── WhatsApp ──────────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    queue="webhooks",
    name="webhooks.process_whatsapp_payload",
)
def process_whatsapp_payload(self, payload: dict):
    """Parse a WhatsApp Cloud API payload and persist to MongoDB."""
    try:
        entry = payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})

        messages = value.get("messages", [])
        if not messages:
            return  # Delivery receipts / status updates

        contacts = {
            c["wa_id"]: c.get("profile", {}).get("name", "Unknown")
            for c in value.get("contacts", [])
        }
        metadata = value.get("metadata", {})
        phone_number_id = metadata.get("phone_number_id", "")

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
            _trigger_ai(conversation, message, integration)

    except Exception as exc:
        logger.exception("Error processing WhatsApp payload: %s", exc)
        raise self.retry(exc=exc)


def _extract_whatsapp_content(msg: dict, msg_type: str) -> str:
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


# ── Messenger ─────────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    queue="webhooks",
    name="webhooks.process_messenger_payload",
)
def process_messenger_payload(self, payload: dict):
    """Parse Facebook Messenger payload and persist to MongoDB."""
    try:
        for entry in payload.get("entry", []):
            page_id = entry.get("id", "")

            try:
                integration = ChannelIntegration.objects.select_related("workspace").get(
                    platform=ChannelIntegration.Platform.MESSENGER,
                    page_id=page_id,
                    is_active=True,
                )
            except ChannelIntegration.DoesNotExist:
                logger.warning("No active Messenger integration for page_id=%s", page_id)
                continue

            workspace_id = str(integration.workspace_id)
            conv_repo = ConversationRepository()
            msg_repo = MessageRepository()

            for messaging in entry.get("messaging", []):
                msg = messaging.get("message", {})
                if not msg or msg.get("is_echo"):
                    continue

                sender_id = messaging.get("sender", {}).get("id", "")
                content = msg.get("text") or "[Attachment]"
                msg_type = "text" if msg.get("text") else "attachment"

                conversation, _ = conv_repo.get_or_create(
                    workspace_id=workspace_id,
                    platform="messenger",
                    contact_id=sender_id,
                    contact_name=sender_id,
                    channel_integration_id=str(integration.id),
                )

                message = build_message(
                    conversation_id=conversation["_id"],
                    workspace_id=workspace_id,
                    platform="messenger",
                    direction="inbound",
                    sender_id=sender_id,
                    sender_name=sender_id,
                    message_type=msg_type,
                    content=content,
                    raw_payload=messaging,
                    platform_message_id=msg.get("mid", ""),
                )
                msg_repo.insert(message)
                conv_repo.update_last_message(conversation["_id"], content)
                _broadcast_new_message(workspace_id, message, conversation)
                _trigger_ai(conversation, message, integration)

    except Exception as exc:
        logger.exception("Error processing Messenger payload: %s", exc)
        raise self.retry(exc=exc)


# ── Telegram ──────────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    queue="webhooks",
    name="webhooks.process_telegram_payload",
)
def process_telegram_payload(self, payload: dict, secret_token: str):
    """
    Parse a Telegram Update object and persist to MongoDB.

    Lookup: integration.verify_token == X-Telegram-Bot-Api-Secret-Token header.
    Set the secret_token when calling setWebhook on the Telegram Bot API.
    """
    try:
        # Look up integration by the webhook secret token
        try:
            integration = ChannelIntegration.objects.select_related("workspace").get(
                platform=ChannelIntegration.Platform.TELEGRAM,
                verify_token=secret_token,
                is_active=True,
            )
        except ChannelIntegration.DoesNotExist:
            logger.warning(
                "No active Telegram integration for secret_token=%.8s…", secret_token
            )
            return

        workspace_id = str(integration.workspace_id)
        conv_repo = ConversationRepository()
        msg_repo = MessageRepository()

        # Extract the message object from the Update
        msg = (
            payload.get("message")
            or payload.get("edited_message")
            or payload.get("channel_post")
        )
        callback = payload.get("callback_query")

        if callback:
            # Button press — treat as a text message with the callback data
            sender = callback.get("from", {})
            chat_id = str(callback.get("message", {}).get("chat", {}).get("id", sender.get("id", "")))
            content = f"[Button: {callback.get('data', '')}]"
            msg_type = "text"
            update_id = str(payload.get("update_id", ""))
        elif msg:
            sender = msg.get("from") or msg.get("sender_chat") or {}
            chat_id = str(msg.get("chat", {}).get("id", sender.get("id", "")))
            msg_type = _get_telegram_message_type(msg)
            content = _extract_telegram_content(msg)
            update_id = str(payload.get("update_id", ""))
        else:
            # Other update types (inline query, poll, etc.) — skip
            return

        sender_id = str(sender.get("id", chat_id))
        first = sender.get("first_name", "")
        last = sender.get("last_name", "")
        sender_name = f"{first} {last}".strip() or sender.get("username", sender_id)

        conversation, _ = conv_repo.get_or_create(
            workspace_id=workspace_id,
            platform="telegram",
            contact_id=chat_id,
            contact_name=sender_name,
            channel_integration_id=str(integration.id),
        )

        message = build_message(
            conversation_id=conversation["_id"],
            workspace_id=workspace_id,
            platform="telegram",
            direction="inbound",
            sender_id=sender_id,
            sender_name=sender_name,
            message_type=msg_type,
            content=content,
            raw_payload=payload,
            platform_message_id=update_id,
        )
        msg_repo.insert(message)
        conv_repo.update_last_message(conversation["_id"], content)
        _broadcast_new_message(workspace_id, message, conversation)
        _trigger_ai(conversation, message, integration)

    except Exception as exc:
        logger.exception("Error processing Telegram payload: %s", exc)
        raise self.retry(exc=exc)


def _get_telegram_message_type(msg: dict) -> str:
    if msg.get("text"):
        return "text"
    if msg.get("photo"):
        return "image"
    if msg.get("voice") or msg.get("audio"):
        return "audio"
    if msg.get("video"):
        return "video"
    if msg.get("document"):
        return "document"
    if msg.get("location"):
        return "location"
    if msg.get("sticker"):
        return "sticker"
    return "text"


def _extract_telegram_content(msg: dict) -> str:
    if msg.get("text"):
        return msg["text"]
    caption = msg.get("caption", "")
    if msg.get("photo"):
        return f"[Photo]{': ' + caption if caption else ''}"
    if msg.get("voice"):
        return "[Voice message]"
    if msg.get("audio"):
        title = msg["audio"].get("title") or msg["audio"].get("file_name", "audio")
        return f"[Audio: {title}]"
    if msg.get("video"):
        return f"[Video]{': ' + caption if caption else ''}"
    if msg.get("document"):
        filename = msg["document"].get("file_name", "file")
        return f"[Document: {filename}]"
    if msg.get("location"):
        loc = msg["location"]
        return f"[Location: {loc.get('latitude')}, {loc.get('longitude')}]"
    if msg.get("sticker"):
        emoji = msg["sticker"].get("emoji", "")
        return f"[Sticker {emoji}]"
    return "[Unsupported message type]"


# ── Facebook Feed (comments) ──────────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    queue="webhooks",
    name="webhooks.process_feed_event",
)
def process_feed_event(self, value: dict, page_id: str):
    """
    Route a Facebook feed-change event (comment add) to the
    automation comment moderation task.
    """
    try:
        from apps.automation.tasks import moderate_comment_task
        moderate_comment_task.apply_async(
            args=[value, page_id],
            queue="ai_responses",
            countdown=0,
        )
    except Exception as exc:
        logger.exception("Error routing feed event to moderation: %s", exc)
        raise self.retry(exc=exc)


# ── Discord ───────────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    queue="webhooks",
    name="webhooks.process_discord_payload",
)
def process_discord_payload(self, payload: dict, guild_id: str):
    """
    Parse a Discord Interaction payload and persist to MongoDB.

    type 2 = APPLICATION_COMMAND (slash command)
    type 3 = MESSAGE_COMPONENT (button/select interaction)

    Note: regular Discord messages need the Gateway WebSocket (discord.py bot),
    not an Interactions Endpoint. This handler covers slash command interactions.
    """
    try:
        interaction_type = payload.get("type")
        if interaction_type not in (2, 3):
            return

        # Look up integration by guild_id
        try:
            integration = ChannelIntegration.objects.select_related("workspace").get(
                platform=ChannelIntegration.Platform.DISCORD,
                discord_guild_id=guild_id,
                is_active=True,
            )
        except ChannelIntegration.DoesNotExist:
            logger.warning("No active Discord integration for guild_id=%s", guild_id)
            return

        workspace_id = str(integration.workspace_id)

        # Extract sender and content
        user = payload.get("member", {}).get("user", {}) or payload.get("user", {})
        sender_id = user.get("id", "")
        sender_name = f"{user.get('username', sender_id)}#{user.get('discriminator', '0')}"

        if interaction_type == 2:
            # Slash command
            data = payload.get("data", {})
            cmd_name = data.get("name", "")
            options = data.get("options", [])
            option_str = " ".join(
                f"{o.get('name')}={o.get('value', '')}" for o in options
            )
            content = f"/{cmd_name}" + (f" {option_str}" if option_str else "")
        else:
            # Component interaction (button press, etc.)
            data = payload.get("data", {})
            content = f"[Interaction: {data.get('custom_id', 'unknown')}]"

        # Use channel_id as contact_id (one conversation per channel per workspace)
        channel_id = payload.get("channel_id", guild_id)

        conv_repo = ConversationRepository()
        msg_repo = MessageRepository()

        conversation, _ = conv_repo.get_or_create(
            workspace_id=workspace_id,
            platform="discord",
            contact_id=channel_id,
            contact_name=f"#{payload.get('channel', {}).get('name', channel_id)}",
            channel_integration_id=str(integration.id),
        )

        message = build_message(
            conversation_id=conversation["_id"],
            workspace_id=workspace_id,
            platform="discord",
            direction="inbound",
            sender_id=sender_id,
            sender_name=sender_name,
            message_type="text",
            content=content,
            raw_payload=payload,
            platform_message_id=payload.get("id", ""),
        )
        msg_repo.insert(message)
        conv_repo.update_last_message(conversation["_id"], content)
        _broadcast_new_message(workspace_id, message, conversation)
        _trigger_ai(conversation, message, integration)

    except Exception as exc:
        logger.exception("Error processing Discord payload: %s", exc)
        raise self.retry(exc=exc)
