from django.urls import path
from .views import ToggleBotView, AssignAgentView, WebhookInfoView, SendTestMessageView

urlpatterns = [
    path("conversations/<str:conversation_id>/bot/", ToggleBotView.as_view(), name="toggle-bot"),
    path("conversations/<str:conversation_id>/assign/", AssignAgentView.as_view(), name="assign-agent"),
    path("webhook-info/", WebhookInfoView.as_view(), name="webhook-info"),
    path("send-test/", SendTestMessageView.as_view(), name="send-test"),
]
