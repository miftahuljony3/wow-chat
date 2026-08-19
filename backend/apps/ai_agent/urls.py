from django.urls import path
from .views import ToggleBotView, AssignAgentView

urlpatterns = [
    path("conversations/<str:conversation_id>/bot/", ToggleBotView.as_view(), name="toggle-bot"),
    path("conversations/<str:conversation_id>/assign/", AssignAgentView.as_view(), name="assign-agent"),
]
