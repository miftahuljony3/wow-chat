from rest_framework import viewsets, permissions, parsers, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import AutoPostConfig, CloudMediaManager, CommentModerationLog, DailyPostLog
from .serializers import (
    AutoPostConfigSerializer,
    CloudMediaSerializer,
    CommentModerationLogSerializer,
    DailyPostLogSerializer,
)


class AutoPostConfigViewSet(viewsets.ModelViewSet):
    serializer_class = AutoPostConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AutoPostConfig.objects.filter(
            workspace=self.request.user.workspace
        ).select_related("integration")

    @action(detail=True, methods=["post"])
    def trigger_now(self, request, pk=None):
        """Manually trigger an auto-post right now (ignores post_time and today guard)."""
        config = self.get_object()
        from .tasks import execute_auto_post
        # Reset today-guard so it posts even if already posted today
        config.last_post_date = None
        config.save(update_fields=["last_post_date"])
        execute_auto_post.apply_async(args=[str(config.id)], queue="default")
        return Response({"detail": "Auto-post task queued."})

    @action(detail=True, methods=["get"])
    def post_logs(self, request, pk=None):
        config = self.get_object()
        logs = DailyPostLog.objects.filter(config=config)[:30]
        return Response(DailyPostLogSerializer(logs, many=True).data)

    @action(detail=True, methods=["get"])
    def moderation_logs(self, request, pk=None):
        config = self.get_object()
        logs = CommentModerationLog.objects.filter(
            integration=config.integration
        )[:50]
        return Response(CommentModerationLogSerializer(logs, many=True).data)


class CloudMediaViewSet(viewsets.ModelViewSet):
    serializer_class = CloudMediaSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_queryset(self):
        qs = CloudMediaManager.objects.filter(workspace=self.request.user.workspace)
        if self.request.query_params.get("unused_only"):
            qs = qs.filter(is_used=False)
        return qs

    @action(detail=True, methods=["post"])
    def mark_unused(self, request, pk=None):
        """Reset a used media file so it can be posted again."""
        media = self.get_object()
        media.is_used = False
        media.used_at = None
        media.used_in_post_id = ""
        media.save(update_fields=["is_used", "used_at", "used_in_post_id"])
        return Response({"detail": "Media marked as unused."})

    @action(detail=False, methods=["post"])
    def bulk_mark_unused(self, request):
        """Reset all used media files for this workspace."""
        count = CloudMediaManager.objects.filter(
            workspace=request.user.workspace, is_used=True
        ).update(is_used=False, used_at=None, used_in_post_id="")
        return Response({"detail": f"{count} files reset."})
