"""
Public HTTP endpoints for the web chat widget.

POST /api/v1/webchat/session/
  Body: { widget_key, session_id? }
  Returns: { session_id, bot_name, welcome_message, primary_color, resumed }
  Creates a new 24-hour session in Redis (or refreshes an existing one).
"""

import json
import uuid

import redis
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.channels_integration.models import ChannelIntegration

_SESSION_TTL = 86400  # 24 hours


def _redis():
    return redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)


class WebChatSessionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        widget_key = request.data.get("widget_key") or request.query_params.get("key")
        if not widget_key:
            return Response({"error": "widget_key required"}, status=400)

        try:
            integration = ChannelIntegration.objects.select_related("workspace").get(
                web_chat_widget_key=widget_key,
                platform="web_chat",
                is_active=True,
            )
        except ChannelIntegration.DoesNotExist:
            return Response({"error": "Invalid widget key"}, status=404)

        r = _redis()

        # Try to resume existing session
        existing_session_id = request.data.get("session_id")
        if existing_session_id:
            raw = r.get(f"webchat:{existing_session_id}")
            if raw:
                r.expire(f"webchat:{existing_session_id}", _SESSION_TTL)
                return Response({
                    "session_id": existing_session_id,
                    "bot_name": integration.display_name or "AI Assistant",
                    "welcome_message": "Welcome back! How can I help you?",
                    "primary_color": "#6366f1",
                    "resumed": True,
                })

        # Create new session
        session_id = str(uuid.uuid4())
        session_data = {
            "integration_id": str(integration.id),
            "workspace_id": str(integration.workspace_id),
            "widget_key": widget_key,
        }
        r.setex(f"webchat:{session_id}", _SESSION_TTL, json.dumps(session_data))

        return Response({
            "session_id": session_id,
            "bot_name": integration.display_name or "AI Assistant",
            "welcome_message": "Hi! How can I help you today? 👋",
            "primary_color": "#6366f1",
            "resumed": False,
        }, status=201)
