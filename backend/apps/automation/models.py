import uuid
from django.db import models
from apps.accounts.models import Workspace
from apps.channels_integration.models import ChannelIntegration


def _media_upload_path(instance, filename):
    return f"auto_post/{instance.workspace_id}/{filename}"


class CloudMediaManager(models.Model):
    """
    Tracks media files (images/videos) used for automated daily Facebook posts.
    Files are stored in MEDIA_ROOT/auto_post/<workspace_id>/.
    The Celery task picks the oldest unused file, marks it used, then posts it.
    """

    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="media_files"
    )
    file = models.FileField(upload_to=_media_upload_path)
    file_name = models.CharField(max_length=255, editable=False)
    media_type = models.CharField(max_length=10, choices=MediaType.choices, default=MediaType.IMAGE)
    is_used = models.BooleanField(default=False, db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    used_in_post_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Cloud Media"
        verbose_name_plural = "Cloud Media"

    def save(self, *args, **kwargs):
        if not self.file_name and self.file:
            self.file_name = self.file.name.split("/")[-1]
        if self.file and not self.media_type:
            name_lower = self.file.name.lower()
            if any(name_lower.endswith(ext) for ext in (".mp4", ".mov", ".avi", ".mkv")):
                self.media_type = self.MediaType.VIDEO
            else:
                self.media_type = self.MediaType.IMAGE
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.file_name} ({'used' if self.is_used else 'unused'})"


class AutoPostConfig(models.Model):
    """
    Per-integration configuration for automated daily Facebook page posting
    and AI comment moderation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="auto_post_configs"
    )
    integration = models.OneToOneField(
        ChannelIntegration,
        on_delete=models.CASCADE,
        related_name="auto_post_config",
        limit_choices_to={"platform__in": ["messenger", "instagram"]},
    )

    # ── Auto-posting ──────────────────────────────────────────────────────────
    is_auto_post_enabled = models.BooleanField(default=False)
    post_time = models.TimeField(
        default="09:00",
        help_text="UTC time to publish the daily post (HH:MM).",
    )
    niche_keywords = models.CharField(
        max_length=300,
        blank=True,
        help_text="Comma-separated keywords describing the page niche (e.g. 'fitness, weight loss, gym').",
    )
    custom_caption_prompt = models.TextField(
        blank=True,
        help_text="Override the default caption-generation system prompt.",
    )
    last_post_date = models.DateField(null=True, blank=True)
    total_posts_published = models.PositiveIntegerField(default=0)

    # ── Comment moderation ────────────────────────────────────────────────────
    spam_deletion_enabled = models.BooleanField(default=True)
    auto_reply_enabled = models.BooleanField(default=True)
    moderation_prompt = models.TextField(
        blank=True,
        help_text="Additional context for the AI moderator (e.g. page rules, topics to ignore).",
    )

    # ── Auto-reply behaviour ──────────────────────────────────────────────────
    class ReplyLanguage(models.TextChoices):
        AUTO = "auto", "Match commenter's language"
        ENGLISH = "en", "English"
        BENGALI = "bn", "Bengali"
        HINDI = "hi", "Hindi"
        ARABIC = "ar", "Arabic"
        SPANISH = "es", "Spanish"

    reply_persona = models.TextField(
        blank=True,
        help_text="Tone / personality for AI replies (e.g. 'friendly and upbeat, uses the customer's name, adds one emoji').",
    )
    business_context = models.TextField(
        blank=True,
        help_text="Facts the AI can use when replying — hours, prices, location, products, FAQs.",
    )
    reply_language = models.CharField(
        max_length=8, choices=ReplyLanguage.choices, default=ReplyLanguage.AUTO,
    )
    like_valid_comments = models.BooleanField(
        default=False, help_text="Also 'like' comments classified as valid."
    )
    reply_only_to_questions = models.BooleanField(
        default=False,
        help_text="Only auto-reply when the comment is a question or clearly expects a response.",
    )
    total_replies_sent = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Auto-Post Config"
        verbose_name_plural = "Auto-Post Configs"

    def __str__(self):
        return f"{self.workspace} – {self.integration.display_name or self.integration.page_id}"


class CommentAutoReplyRule(models.Model):
    """
    Keyword-triggered canned reply. Checked BEFORE the AI on valid comments —
    the first active matching rule wins and replies instantly (deterministic,
    no LLM call). Useful for FAQs like price, delivery, location, booking.
    """

    class MatchType(models.TextChoices):
        ANY = "any", "Match ANY keyword"
        ALL = "all", "Match ALL keywords"
        EXACT = "exact", "Exact phrase"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    config = models.ForeignKey(
        AutoPostConfig, on_delete=models.CASCADE, related_name="reply_rules"
    )
    name = models.CharField(max_length=100, blank=True)
    keywords = models.CharField(
        max_length=500,
        help_text="Comma-separated trigger keywords (e.g. 'price, cost, how much').",
    )
    match_type = models.CharField(
        max_length=8, choices=MatchType.choices, default=MatchType.ANY
    )
    reply_text = models.TextField(help_text="The canned reply to post.")
    is_active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(
        default=0, help_text="Higher priority rules are checked first."
    )
    times_triggered = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-priority", "created_at"]
        verbose_name = "Comment Auto-Reply Rule"
        verbose_name_plural = "Comment Auto-Reply Rules"

    def __str__(self):
        return f"{self.name or self.keywords[:30]} → {self.reply_text[:30]}"

    def matches(self, text: str) -> bool:
        """True if `text` triggers this rule per its match_type."""
        if not text:
            return False
        haystack = text.lower()
        kws = [k.strip().lower() for k in self.keywords.split(",") if k.strip()]
        if not kws:
            return False
        if self.match_type == self.MatchType.EXACT:
            return any(k == haystack.strip() for k in kws)
        if self.match_type == self.MatchType.ALL:
            return all(k in haystack for k in kws)
        return any(k in haystack for k in kws)


class CommentModerationLog(models.Model):
    """Audit trail for every comment the AI moderator processed."""

    class Action(models.TextChoices):
        DELETED = "deleted", "Deleted (spam/abusive)"
        REPLIED = "replied", "Replied (valid)"
        IGNORED = "ignored", "Ignored (no action)"
        ERROR = "error", "Error"

    class Verdict(models.TextChoices):
        SPAM = "spam", "Spam"
        ABUSIVE = "abusive", "Abusive"
        VALID = "valid", "Valid"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="moderation_logs"
    )
    integration = models.ForeignKey(
        ChannelIntegration,
        on_delete=models.SET_NULL,
        null=True,
        related_name="moderation_logs",
    )
    comment_id = models.CharField(max_length=100, db_index=True)
    post_id = models.CharField(max_length=100, blank=True)
    author_id = models.CharField(max_length=100, blank=True)
    author_name = models.CharField(max_length=200, blank=True)
    comment_text = models.TextField()
    ai_verdict = models.CharField(max_length=20, choices=Verdict.choices)
    ai_reply = models.TextField(blank=True)
    action = models.CharField(max_length=20, choices=Action.choices)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Comment Moderation Log"
        verbose_name_plural = "Comment Moderation Logs"

    def __str__(self):
        return f"{self.author_name}: {self.comment_text[:40]} → {self.action}"


class DailyPostLog(models.Model):
    """Record of each auto-post attempt."""

    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        NO_MEDIA = "no_media", "No Media Available"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    config = models.ForeignKey(
        AutoPostConfig, on_delete=models.CASCADE, related_name="post_logs"
    )
    media = models.ForeignKey(
        CloudMediaManager, on_delete=models.SET_NULL, null=True, blank=True
    )
    status = models.CharField(max_length=20, choices=Status.choices)
    fb_post_id = models.CharField(max_length=100, blank=True)
    caption_used = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.config} – {self.created_at.date()} – {self.status}"
