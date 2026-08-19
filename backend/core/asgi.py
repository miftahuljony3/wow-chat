import os
import django
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from apps.inbox.middleware import JWTAuthMiddlewareStack
import apps.inbox.routing as inbox_routing

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddlewareStack(
                URLRouter(inbox_routing.websocket_urlpatterns)
            )
        ),
    }
)
