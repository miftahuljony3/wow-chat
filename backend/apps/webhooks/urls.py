from django.urls import path
from .views import WhatsAppWebhookView, MessengerWebhookView

urlpatterns = [
    path("whatsapp/", WhatsAppWebhookView.as_view(), name="webhook-whatsapp"),
    path("messenger/", MessengerWebhookView.as_view(), name="webhook-messenger"),
]
