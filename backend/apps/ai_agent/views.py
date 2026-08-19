from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

from apps.inbox.mongo import ConversationRepository
from apps.channels_integration.models import ChannelIntegration
from .services import WhatsAppService
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


class WebhookInfoView(APIView):
    """Return webhook URL and verify token so the frontend can display setup instructions."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            "webhook_url": f"{settings.SITE_BASE_URL}/webhooks/whatsapp/",
            "verify_token": settings.WHATSAPP_VERIFY_TOKEN,
        })


class SendTestMessageView(APIView):
    """
    Send a test WhatsApp message via a saved integration.
    Used from the Settings page to verify credentials work.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        integration_id = request.data.get("integration_id")
        to = request.data.get("to", "").strip().replace(" ", "").replace("-", "")
        message = request.data.get(
            "message",
            "👋 Hello from Wow Chat! Your WhatsApp integration is working correctly."
        )

        if not integration_id:
            return Response(
                {"error": "integration_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not to:
            return Response(
                {"error": "Recipient phone number (to) is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Ensure country code prefix (no +)
        to = to.lstrip("+")

        try:
            integration = ChannelIntegration.objects.get(
                id=integration_id,
                workspace=request.user.workspace,
                is_active=True,
            )
        except ChannelIntegration.DoesNotExist:
            return Response(
                {"error": "Integration not found or inactive."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not integration.phone_number_id or not integration.access_token:
            return Response(
                {"error": "Integration is missing Phone Number ID or Access Token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            svc = WhatsAppService(
                phone_number_id=integration.phone_number_id,
                access_token=integration.access_token,
            )
            result = svc.send_text(to=to, body=message)
            return Response({
                "success": True,
                "message_id": result.get("messages", [{}])[0].get("id", ""),
                "result": result,
            })
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
