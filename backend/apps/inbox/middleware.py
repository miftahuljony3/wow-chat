"""
JWT authentication middleware for Django Channels WebSocket connections.
Reads the token from the query string: ws://host/ws/inbox/?token=<jwt>
"""

from urllib.parse import parse_qs
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_key: str):
    try:
        token = AccessToken(token_key)
        return User.objects.select_related("workspace").get(id=token["user_id"])
    except (TokenError, User.DoesNotExist):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        qs = parse_qs(scope.get("query_string", b"").decode())
        token_key = qs.get("token", [None])[0]

        if token_key:
            scope["user"] = await get_user_from_token(token_key)
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
