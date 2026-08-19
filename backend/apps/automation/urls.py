from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AutoPostConfigViewSet, CloudMediaViewSet

router = DefaultRouter()
router.register(r"configs", AutoPostConfigViewSet, basename="auto-post-config")
router.register(r"media", CloudMediaViewSet, basename="cloud-media")

urlpatterns = [path("", include(router.urls))]
