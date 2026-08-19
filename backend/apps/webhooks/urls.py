from django.urls import path
from .views import (
    WhatsAppWebhookView,
    MessengerWebhookView,
    TelegramWebhookView,
    DiscordWebhookView,
)

urlpatterns = [
    path("whatsapp/", WhatsAppWebhookView.as_view(), name="webhook-whatsapp"),
    path("messenger/", MessengerWebhookView.as_view(), name="webhook-messenger"),
    path("telegram/", TelegramWebhookView.as_view(), name="webhook-telegram"),
    path("discord/", DiscordWebhookView.as_view(), name="webhook-discord"),
]
