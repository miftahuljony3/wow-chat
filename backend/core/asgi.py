import os
import django
from django.core.asgi import get_asgi_application
from django.urls import re_path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from apps.inbox.middleware import JWTAuthMiddlewareStack
from apps.inbox.consumers import InboxConsumer
from apps.webchat.consumers import WebChatConsumer

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": URLRouter(
            [
                # Web chat widget — no origin restriction (embeds on external sites)
                re_path(
                    r"^ws/webchat/(?P<session_id>[0-9a-f-]{36})/$",
                    WebChatConsumer.as_asgi(),
                ),
                # Agent inbox — JWT auth + same-origin enforcement
                re_path(
                    r"^ws/inbox/$",
                    AllowedHostsOriginValidator(
                        JWTAuthMiddlewareStack(InboxConsumer.as_asgi())
                    ),
                ),
            ]
        ),
    }
)
