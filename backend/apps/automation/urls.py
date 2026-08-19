from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AutoPostConfigViewSet,
    CloudMediaViewSet,
    CommentAutoReplyRuleViewSet,
)

router = DefaultRouter()
router.register(r"configs", AutoPostConfigViewSet, basename="auto-post-config")
router.register(r"media", CloudMediaViewSet, basename="cloud-media")
router.register(r"reply-rules", CommentAutoReplyRuleViewSet, basename="reply-rule")

urlpatterns = [path("", include(router.urls))]
