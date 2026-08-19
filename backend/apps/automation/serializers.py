from rest_framework import serializers
from .models import AutoPostConfig, CloudMediaManager, CommentModerationLog, DailyPostLog


class CloudMediaSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = CloudMediaManager
        fields = [
            "id", "file", "file_name", "media_type", "file_url",
            "is_used", "used_at", "used_in_post_id", "created_at",
        ]
        read_only_fields = ["id", "file_name", "file_url", "is_used", "used_at", "used_in_post_id", "created_at"]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None

    def create(self, validated_data):
        validated_data["workspace"] = self.context["request"].user.workspace
        # Auto-detect media type from extension
        file = validated_data.get("file")
        if file:
            name = file.name.lower()
            if any(name.endswith(ext) for ext in (".mp4", ".mov", ".avi", ".mkv", ".webm")):
                validated_data["media_type"] = CloudMediaManager.MediaType.VIDEO
            else:
                validated_data["media_type"] = CloudMediaManager.MediaType.IMAGE
        return super().create(validated_data)


class AutoPostConfigSerializer(serializers.ModelSerializer):
    integration_display = serializers.SerializerMethodField(read_only=True)
    media_unused_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AutoPostConfig
        fields = [
            "id", "integration", "integration_display",
            "is_auto_post_enabled", "post_time", "niche_keywords",
            "custom_caption_prompt", "last_post_date", "total_posts_published",
            "spam_deletion_enabled", "auto_reply_enabled", "moderation_prompt",
            "media_unused_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "last_post_date", "total_posts_published", "created_at", "updated_at"]

    def get_integration_display(self, obj):
        return obj.integration.display_name or obj.integration.page_id

    def get_media_unused_count(self, obj):
        return CloudMediaManager.objects.filter(
            workspace=obj.workspace, is_used=False
        ).count()

    def create(self, validated_data):
        validated_data["workspace"] = self.context["request"].user.workspace
        return super().create(validated_data)


class CommentModerationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentModerationLog
        fields = [
            "id", "comment_id", "post_id", "author_name", "comment_text",
            "ai_verdict", "ai_reply", "action", "error_message", "created_at",
        ]
        read_only_fields = fields


class DailyPostLogSerializer(serializers.ModelSerializer):
    media_file = serializers.SerializerMethodField()

    class Meta:
        model = DailyPostLog
        fields = [
            "id", "status", "fb_post_id", "caption_used",
            "media_file", "error_message", "created_at",
        ]
        read_only_fields = fields

    def get_media_file(self, obj):
        if obj.media:
            return {"id": str(obj.media.id), "file_name": obj.media.file_name}
        return None
