from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChannelIntegrationViewSet

router = DefaultRouter()
router.register(r"integrations", ChannelIntegrationViewSet, basename="channel-integration")

urlpatterns = [path("", include(router.urls))]
