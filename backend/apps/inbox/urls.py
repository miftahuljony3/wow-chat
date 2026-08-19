from django.urls import path
from .views import ConversationListView, MessageListView, MarkReadView

urlpatterns = [
    path("conversations/", ConversationListView.as_view(), name="conversations"),
    path("conversations/<str:conversation_id>/messages/", MessageListView.as_view(), name="messages"),
    path("conversations/<str:conversation_id>/read/", MarkReadView.as_view(), name="mark-read"),
]
