from rest_framework import serializers
from .models import ChannelIntegration


class ChannelIntegrationSerializer(serializers.ModelSerializer):
    # Write-only sensitive fields
    access_token = serializers.CharField(write_only=True, required=False, allow_blank=True)
    page_access_token = serializers.CharField(write_only=True, required=False, allow_blank=True)
    telegram_bot_token = serializers.CharField(write_only=True, required=False, allow_blank=True)
    discord_bot_token = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = ChannelIntegration
        fields = [
            "id", "platform", "display_name", "is_active",
            # WhatsApp
            "phone_number_id", "access_token", "waba_id", "app_secret",
            # Messenger / Instagram
            "page_id", "page_access_token", "instagram_business_account_id",
            # Telegram
            "telegram_bot_token", "telegram_bot_username",
            # Discord
            "discord_bot_token", "discord_guild_id", "discord_channel_id",
            # Web Chat
            "web_chat_widget_key", "web_chat_allowed_origins",
            # AI
            "ai_enabled", "ai_system_prompt", "ai_handoff_keywords",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "web_chat_widget_key"]

    def _maybe_resolve_page_token(self, validated_data, instance=None):
        """For Messenger/Instagram, swap a User/wrong token for the correct
        Page access token and stash a human-readable resolution note."""
        platform = validated_data.get("platform") or (instance.platform if instance else None)
        if platform not in ("messenger", "instagram"):
            return
        token = validated_data.get("page_access_token")
        if not token:
            return
        page_id = validated_data.get("page_id") or (instance.page_id if instance else "")
        from .graph import resolve_page_access_token
        resolved, info = resolve_page_access_token(token, page_id)
        validated_data["page_access_token"] = resolved
        self._token_info = info

    def create(self, validated_data):
        validated_data["workspace"] = self.context["request"].user.workspace
        # Auto-generate web chat widget key
        if validated_data.get("platform") == "web_chat" and not validated_data.get("web_chat_widget_key"):
            import secrets
            validated_data["web_chat_widget_key"] = secrets.token_urlsafe(32)
        self._maybe_resolve_page_token(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._maybe_resolve_page_token(validated_data, instance=instance)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        info = getattr(self, "_token_info", None)
        if info is not None:
            data["token_resolution"] = info
        return data
