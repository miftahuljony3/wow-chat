from django.contrib import admin
from .models import CloudMediaManager, AutoPostConfig, CommentModerationLog, DailyPostLog


@admin.register(CloudMediaManager)
class CloudMediaAdmin(admin.ModelAdmin):
    list_display = ["file_name", "workspace", "media_type", "is_used", "used_at", "created_at"]
    list_filter = ["is_used", "media_type", "workspace"]
    search_fields = ["file_name"]
    readonly_fields = ["file_name", "is_used", "used_at", "used_in_post_id", "created_at"]


@admin.register(AutoPostConfig)
class AutoPostConfigAdmin(admin.ModelAdmin):
    list_display = [
        "workspace", "integration", "is_auto_post_enabled",
        "post_time", "spam_deletion_enabled", "total_posts_published", "last_post_date",
    ]
    list_filter = ["is_auto_post_enabled", "spam_deletion_enabled", "workspace"]
    readonly_fields = ["last_post_date", "total_posts_published", "created_at", "updated_at"]


@admin.register(CommentModerationLog)
class CommentModerationLogAdmin(admin.ModelAdmin):
    list_display = [
        "author_name", "ai_verdict", "action", "workspace", "created_at"
    ]
    list_filter = ["ai_verdict", "action", "workspace"]
    search_fields = ["comment_text", "author_name", "comment_id"]
    readonly_fields = list(
        f.name for f in CommentModerationLog._meta.fields
    )


@admin.register(DailyPostLog)
class DailyPostLogAdmin(admin.ModelAdmin):
    list_display = ["config", "status", "fb_post_id", "created_at"]
    list_filter = ["status"]
    readonly_fields = ["config", "media", "status", "fb_post_id", "caption_used", "error_message", "created_at"]
