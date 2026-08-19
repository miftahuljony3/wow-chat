"""
MongoDB repository layer for Conversations and Messages.
Uses pymongo (sync) — call from Celery workers and DRF views.
Motor (async) is available for Channels consumers if needed.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from django.conf import settings
from pymongo import MongoClient, DESCENDING
from pymongo.collection import Collection


def _get_db():
    client = MongoClient(settings.MONGO_URI)
    return client[settings.MONGODB["DB"]]


# ── Schema helpers ────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_message(
    *,
    conversation_id: str,
    workspace_id: str,
    platform: str,            # "whatsapp" | "messenger"
    direction: str,           # "inbound" | "outbound"
    sender_id: str,
    sender_name: str,
    message_type: str,        # "text" | "image" | "audio" | "document"
    content: str,
    raw_payload: dict,
    platform_message_id: str = "",
    agent_id: Optional[str] = None,
) -> dict:
    """Return a standardised Message document."""
    return {
        "_id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "workspace_id": workspace_id,
        "platform": platform,
        "direction": direction,
        "sender_id": sender_id,
        "sender_name": sender_name,
        "message_type": message_type,
        "content": content,
        "platform_message_id": platform_message_id,
        "raw_payload": raw_payload,
        "agent_id": agent_id,
        "is_read": False,
        "created_at": _now(),
    }


def build_conversation(
    *,
    workspace_id: str,
    platform: str,
    contact_id: str,           # phone number or PSID
    contact_name: str,
    channel_integration_id: str,
) -> dict:
    """Return a new Conversation document."""
    return {
        "_id": str(uuid.uuid4()),
        "workspace_id": workspace_id,
        "platform": platform,
        "contact_id": contact_id,
        "contact_name": contact_name,
        "channel_integration_id": channel_integration_id,
        "bot_active": True,       # AI auto-responder on by default
        "assigned_agent_id": None,
        "status": "open",         # "open" | "resolved" | "pending"
        "last_message_at": _now(),
        "last_message_preview": "",
        "unread_count": 0,
        "created_at": _now(),
        "updated_at": _now(),
    }


# ── Repository ────────────────────────────────────────────────────────────────

class ConversationRepository:
    def __init__(self):
        db = _get_db()
        self._col: Collection = db["conversations"]
        # Ensure indexes
        self._col.create_index([("workspace_id", 1), ("contact_id", 1), ("platform", 1)])
        self._col.create_index([("workspace_id", 1), ("last_message_at", DESCENDING)])

    def get_or_create(
        self,
        *,
        workspace_id: str,
        platform: str,
        contact_id: str,
        contact_name: str,
        channel_integration_id: str,
    ) -> tuple[dict, bool]:
        """
        Return (conversation, created).
        contact_id + platform + workspace_id form the natural key.
        """
        existing = self._col.find_one(
            {
                "workspace_id": workspace_id,
                "platform": platform,
                "contact_id": contact_id,
            }
        )
        if existing:
            return existing, False

        doc = build_conversation(
            workspace_id=workspace_id,
            platform=platform,
            contact_id=contact_id,
            contact_name=contact_name,
            channel_integration_id=channel_integration_id,
        )
        self._col.insert_one(doc)
        return doc, True

    def list_for_workspace(
        self,
        workspace_id: str,
        status: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> list[dict]:
        query: dict = {"workspace_id": workspace_id}
        if status:
            query["status"] = status
        return list(
            self._col.find(query)
            .sort("last_message_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )

    def update_last_message(
        self, conversation_id: str, preview: str, increment_unread: bool = True
    ):
        update: dict = {
            "$set": {
                "last_message_at": _now(),
                "last_message_preview": preview[:80],
                "updated_at": _now(),
            }
        }
        if increment_unread:
            update["$inc"] = {"unread_count": 1}
        self._col.update_one({"_id": conversation_id}, update)

    def set_bot_active(self, conversation_id: str, active: bool):
        self._col.update_one(
            {"_id": conversation_id},
            {"$set": {"bot_active": active, "updated_at": _now()}},
        )

    def assign_agent(self, conversation_id: str, agent_id: Optional[str]):
        self._col.update_one(
            {"_id": conversation_id},
            {"$set": {"assigned_agent_id": agent_id, "updated_at": _now()}},
        )

    def get_by_id(self, conversation_id: str) -> Optional[dict]:
        return self._col.find_one({"_id": conversation_id})


class MessageRepository:
    def __init__(self):
        db = _get_db()
        self._col: Collection = db["messages"]
        self._col.create_index([("conversation_id", 1), ("created_at", DESCENDING)])
        self._col.create_index("workspace_id")

    def insert(self, message: dict) -> dict:
        self._col.insert_one(message)
        return message

    def list_for_conversation(
        self,
        conversation_id: str,
        limit: int = 50,
        skip: int = 0,
    ) -> list[dict]:
        return list(
            self._col.find({"conversation_id": conversation_id})
            .sort("created_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )

    def mark_read(self, conversation_id: str):
        self._col.update_many(
            {"conversation_id": conversation_id, "is_read": False},
            {"$set": {"is_read": True}},
        )
