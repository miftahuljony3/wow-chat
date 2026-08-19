import uuid
from django.db import models
from apps.accounts.models import Workspace


class ChannelIntegration(models.Model):
    """
    Stores platform-specific API credentials for a Workspace.
    One record per platform per workspace.
    """

    class Platform(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp Cloud API"
        MESSENGER = "messenger", "Facebook Messenger"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="channel_integrations"
    )
    platform = models.CharField(max_length=20, choices=Platform.choices)
    display_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    # WhatsApp Cloud API fields
    phone_number_id = models.CharField(max_length=50, blank=True)
    access_token = models.TextField(blank=True)  # encrypted in production
    app_secret = models.CharField(max_length=255, blank=True)
    verify_token = models.CharField(max_length=255, blank=True)
    waba_id = models.CharField("WhatsApp Business Account ID", max_length=50, blank=True)

    # Facebook Messenger fields
    page_id = models.CharField(max_length=50, blank=True)
    page_access_token = models.TextField(blank=True)

    # AI configuration
    ai_enabled = models.BooleanField(default=True)
    ai_system_prompt = models.TextField(
        default=(
            "You are a helpful customer support assistant for {workspace}. "
            "Be concise, friendly, and professional. "
            "If you cannot help, say so and offer to connect them with a human agent."
        )
    )
    ai_handoff_keywords = models.JSONField(
        default=list,
        help_text="Keywords that trigger human handoff (e.g. ['human', 'agent', 'help'])",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("workspace", "platform", "phone_number_id")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.workspace} – {self.get_platform_display()}"
