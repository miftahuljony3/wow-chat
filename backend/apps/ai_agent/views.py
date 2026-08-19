from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from apps.inbox.mongo import ConversationRepository
from .tasks import trigger_human_handoff


class ToggleBotView(APIView):
    """Enable or disable the AI bot for a conversation."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, conversation_id):
        active = request.data.get("bot_active", True)
        workspace_id = str(request.user.workspace_id)

        repo = ConversationRepository()
        repo.set_bot_active(conversation_id, active)

        if not active:
            trigger_human_handoff.apply_async(
                args=[conversation_id, workspace_id],
                queue="ai_responses",
            )

        return Response({"bot_active": active})


class AssignAgentView(APIView):
    """Assign or un-assign a human agent to a conversation."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, conversation_id):
        agent_id = request.data.get("agent_id")
        repo = ConversationRepository()
        repo.assign_agent(conversation_id, agent_id)
        return Response({"assigned_agent_id": agent_id})
