from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/channels/", include("apps.channels_integration.urls")),
    path("api/v1/inbox/", include("apps.inbox.urls")),
    path("api/v1/ai/", include("apps.ai_agent.urls")),
    path("api/v1/automation/", include("apps.automation.urls")),
    # Webhook endpoints — no auth, signed by Meta
    path("webhooks/", include("apps.webhooks.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
