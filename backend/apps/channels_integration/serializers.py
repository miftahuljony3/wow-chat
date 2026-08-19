from rest_framework import serializers
from .models import ChannelIntegration


class ChannelIntegrationSerializer(serializers.ModelSerializer):
    # Never expose raw tokens in list responses
    access_token = serializers.CharField(write_only=True, required=False)
    page_access_token = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = ChannelIntegration
        fields = [
            "id", "platform", "display_name", "is_active",
            "phone_number_id", "access_token", "waba_id",
            "page_id", "page_access_token",
            "ai_enabled", "ai_system_prompt", "ai_handoff_keywords",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        validated_data["workspace"] = self.context["request"].user.workspace
        return super().create(validated_data)
