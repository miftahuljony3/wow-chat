from django.contrib import admin
from .models import ChannelIntegration


@admin.register(ChannelIntegration)
class ChannelIntegrationAdmin(admin.ModelAdmin):
    list_display = ["workspace", "platform", "display_name", "is_active", "ai_enabled"]
    list_filter = ["platform", "is_active", "ai_enabled"]
    search_fields = ["workspace__name", "display_name", "phone_number_id"]
