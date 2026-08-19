"""
Celery tasks for the automation app.

check_and_post       — runs every 5 min, fires execute_auto_post for due configs
execute_auto_post    — picks media, generates caption, publishes to Facebook
moderate_comment_task — classifies + acts on a single comment (delete/reply/ignore)
"""

import logging
from datetime import date, datetime

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ── Scheduled: check which configs are due to post today ─────────────────────

@shared_task(
    name="automation.check_and_post",
    queue="default",
    ignore_result=True,
)
def check_and_post():
    """
    Runs every 5 minutes via Celery Beat.
    Finds AutoPostConfigs whose post_time window has arrived (±5 min, UTC)
    and haven't posted today, then fires execute_auto_post for each.
    """
    from apps.automation.models import AutoPostConfig

    now_utc = timezone.now()
    today = now_utc.date()
    current_minute = now_utc.hour * 60 + now_utc.minute  # minutes since midnight

    configs = (
        AutoPostConfig.objects
        .filter(is_auto_post_enabled=True, integration__is_active=True)
        .exclude(last_post_date=today)
        .select_related("workspace", "integration")
    )

    for config in configs:
        pt = config.post_time
        config_minute = pt.hour * 60 + pt.minute
        delta = abs(current_minute - config_minute)
        # Post within a 5-minute window to avoid missed ticks
        if delta <= 5 or delta >= (24 * 60 - 5):
            logger.info(
                "Auto-post due for config %s (workspace=%s, page=%s)",
                config.id, config.workspace, config.integration.page_id,
            )
            execute_auto_post.apply_async(args=[str(config.id)], queue="default")


# ── Execute a single auto-post ────────────────────────────────────────────────

@shared_task(
    bind=True,
    name="automation.execute_auto_post",
    queue="default",
    max_retries=2,
    default_retry_delay=60,
)
def execute_auto_post(self, config_id: str):
    """
    Full daily-posting pipeline for one AutoPostConfig:
    1. Re-check already-posted-today guard (idempotent)
    2. Pick the oldest unused media file
    3. Generate an AI caption using LangChain + web search
    4. Publish to Facebook Page (photo or video or feed)
    5. Mark media used, update config, write DailyPostLog
    """
    from apps.automation.models import AutoPostConfig, CloudMediaManager, DailyPostLog
    from apps.automation.agents import generate_caption
    from apps.automation.services import FacebookPageService, GraphAPIError

    try:
        config = AutoPostConfig.objects.select_related(
            "workspace", "integration"
        ).get(id=config_id)
    except AutoPostConfig.DoesNotExist:
        logger.error("AutoPostConfig %s not found.", config_id)
        return

    today = timezone.now().date()
    if config.last_post_date == today:
        logger.info("Config %s already posted today, skipping.", config_id)
        return

    # ── Pick media ────────────────────────────────────────────────────────────
    media = (
        CloudMediaManager.objects
        .filter(workspace=config.workspace, is_used=False)
        .order_by("created_at")
        .first()
    )

    if not media:
        logger.warning(
            "No unused media for workspace %s, config %s.",
            config.workspace, config_id,
        )
        DailyPostLog.objects.create(
            config=config,
            status=DailyPostLog.Status.NO_MEDIA,
            error_message="No unused media files available.",
        )
        return

    # ── Generate caption ──────────────────────────────────────────────────────
    try:
        caption = generate_caption(
            niche=config.niche_keywords,
            media_type=media.media_type,
            custom_prompt=config.custom_caption_prompt,
        )
    except Exception as exc:
        caption = f"✨ Check out our latest {media.media_type}! What do you think? 👇"
        logger.warning("Caption generation failed, using fallback: %s", exc)

    # ── Build public media URL ────────────────────────────────────────────────
    media_url = f"{settings.SITE_BASE_URL}{settings.MEDIA_URL}{media.file.name}"

    # ── Publish to Facebook ───────────────────────────────────────────────────
    integration = config.integration
    svc = FacebookPageService(
        page_access_token=integration.page_access_token,
        page_id=integration.page_id,
    )

    fb_post_id = ""
    try:
        if media.media_type == CloudMediaManager.MediaType.IMAGE:
            result = svc.post_photo(image_url=media_url, caption=caption)
        elif media.media_type == CloudMediaManager.MediaType.VIDEO:
            result = svc.post_video(video_url=media_url, description=caption)
        else:
            result = svc.post_feed(message=caption)

        fb_post_id = result.get("id", result.get("post_id", ""))
        logger.info("Published post %s for config %s", fb_post_id, config_id)

    except GraphAPIError as exc:
        # Facebook returned an API error (bad/insufficient token, permission,
        # page mismatch). Not transient — don't retry, just log it legibly.
        logger.error("Graph API rejected post for config %s: %s", config_id, exc)
        DailyPostLog.objects.create(
            config=config,
            media=media,
            status=DailyPostLog.Status.FAILED,
            caption_used=caption,
            error_message=str(exc),
        )
        return
    except Exception as exc:
        logger.exception("Failed to publish post for config %s: %s", config_id, exc)
        DailyPostLog.objects.create(
            config=config,
            media=media,
            status=DailyPostLog.Status.FAILED,
            caption_used=caption,
            error_message=str(exc),
        )
        raise self.retry(exc=exc)

    # ── Mark media used ───────────────────────────────────────────────────────
    media.is_used = True
    media.used_at = timezone.now()
    media.used_in_post_id = fb_post_id
    media.save(update_fields=["is_used", "used_at", "used_in_post_id"])

    # ── Update config ─────────────────────────────────────────────────────────
    config.last_post_date = today
    config.total_posts_published = (config.total_posts_published or 0) + 1
    config.save(update_fields=["last_post_date", "total_posts_published"])

    # ── Log success ───────────────────────────────────────────────────────────
    DailyPostLog.objects.create(
        config=config,
        media=media,
        status=DailyPostLog.Status.SUCCESS,
        fb_post_id=fb_post_id,
        caption_used=caption,
    )


# ── Comment moderation ────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    name="automation.moderate_comment_task",
    queue="ai_responses",
    max_retries=2,
    default_retry_delay=10,
)
def moderate_comment_task(self, event: dict, page_id: str):
    """
    Process a single Facebook comment event from the feed webhook:
    1. Look up the AutoPostConfig for this page
    2. Run AI moderation (spam / abusive / valid)
    3. Act: delete comment if spam/abusive, reply if valid
    4. Write CommentModerationLog
    """
    from apps.automation.models import AutoPostConfig, CommentModerationLog
    from apps.automation.agents import moderate_comment
    from apps.automation.services import FacebookPageService
    from apps.channels_integration.models import ChannelIntegration

    comment_id = event.get("comment_id", "")
    post_id = event.get("post_id", "")
    comment_text = event.get("message", "")
    author_name = event.get("from", {}).get("name", "")
    author_id = event.get("from", {}).get("id", "")

    if not comment_id or not comment_text:
        logger.info("Skipping empty comment event (comment_id=%s)", comment_id)
        return

    # Find integration by page_id
    try:
        integration = ChannelIntegration.objects.select_related("workspace").get(
            page_id=page_id, is_active=True,
        )
    except ChannelIntegration.DoesNotExist:
        logger.warning("No integration for page_id=%s", page_id)
        return

    # Find AutoPostConfig (for moderation settings)
    try:
        config = AutoPostConfig.objects.get(integration=integration)
        spam_delete = config.spam_deletion_enabled
        auto_reply = config.auto_reply_enabled
        niche = config.niche_keywords
        extra_rules = config.moderation_prompt
    except AutoPostConfig.DoesNotExist:
        # No config: use sensible defaults
        spam_delete = True
        auto_reply = False
        niche = ""
        extra_rules = ""

    svc = FacebookPageService(
        page_access_token=integration.page_access_token,
        page_id=page_id,
    )

    # ── AI moderation ─────────────────────────────────────────────────────────
    try:
        result = moderate_comment(
            comment_text=comment_text,
            niche=niche,
            extra_rules=extra_rules,
        )
        verdict = result["verdict"]
        ai_reply = result.get("reply", "")
    except Exception as exc:
        logger.exception("Moderation agent failed for comment %s: %s", comment_id, exc)
        CommentModerationLog.objects.create(
            workspace=integration.workspace,
            integration=integration,
            comment_id=comment_id,
            post_id=post_id,
            author_id=author_id,
            author_name=author_name,
            comment_text=comment_text,
            ai_verdict="valid",
            ai_reply="",
            action=CommentModerationLog.Action.ERROR,
            error_message=str(exc),
        )
        raise self.retry(exc=exc)

    # ── Act ───────────────────────────────────────────────────────────────────
    action = CommentModerationLog.Action.IGNORED
    error_msg = ""

    if verdict in ("spam", "abusive") and spam_delete:
        try:
            svc.delete_comment(comment_id)
            action = CommentModerationLog.Action.DELETED
            logger.info("Deleted %s comment %s from %s", verdict, comment_id, author_name)
        except Exception as exc:
            error_msg = str(exc)
            action = CommentModerationLog.Action.ERROR
            logger.error("Failed to delete comment %s: %s", comment_id, exc)

    elif verdict == "valid" and auto_reply and ai_reply:
        try:
            svc.reply_to_comment(comment_id, ai_reply)
            action = CommentModerationLog.Action.REPLIED
            logger.info("Replied to comment %s from %s", comment_id, author_name)
        except Exception as exc:
            error_msg = str(exc)
            action = CommentModerationLog.Action.ERROR
            logger.error("Failed to reply to comment %s: %s", comment_id, exc)

    CommentModerationLog.objects.create(
        workspace=integration.workspace,
        integration=integration,
        comment_id=comment_id,
        post_id=post_id,
        author_id=author_id,
        author_name=author_name,
        comment_text=comment_text,
        ai_verdict=verdict,
        ai_reply=ai_reply,
        action=action,
        error_message=error_msg,
    )
