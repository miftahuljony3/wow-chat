from rest_framework import viewsets, permissions
from .models import ChannelIntegration
from .serializers import ChannelIntegrationSerializer


class ChannelIntegrationViewSet(viewsets.ModelViewSet):
    serializer_class = ChannelIntegrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChannelIntegration.objects.filter(
            workspace=self.request.user.workspace
        )
