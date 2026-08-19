from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from .mongo import ConversationRepository, MessageRepository

conv_repo = ConversationRepository.__new__(ConversationRepository)
msg_repo = MessageRepository.__new__(MessageRepository)


class ConversationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        workspace_id = str(request.user.workspace_id)
        conv_status = request.query_params.get("status")
        page = int(request.query_params.get("page", 1))
        limit = 50
        skip = (page - 1) * limit

        # Lazy-init repos (avoids DB call at import time)
        repo = ConversationRepository()
        convs = repo.list_for_workspace(
            workspace_id, status=conv_status, limit=limit, skip=skip
        )
        # Convert ObjectId-style _id to string for JSON
        for c in convs:
            c["id"] = c.pop("_id")
        return Response({"results": convs, "page": page})


class MessageListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, conversation_id):
        page = int(request.query_params.get("page", 1))
        limit = 50
        skip = (page - 1) * limit

        repo = MessageRepository()
        msgs = repo.list_for_conversation(conversation_id, limit=limit, skip=skip)
        for m in msgs:
            m["id"] = m.pop("_id")
        return Response({"results": msgs, "page": page})


class MarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, conversation_id):
        repo = MessageRepository()
        repo.mark_read(conversation_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
