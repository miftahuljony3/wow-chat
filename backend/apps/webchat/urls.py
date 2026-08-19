from django.urls import path
from .views import WebChatSessionView

urlpatterns = [
    path("session/", WebChatSessionView.as_view(), name="webchat-session"),
]
