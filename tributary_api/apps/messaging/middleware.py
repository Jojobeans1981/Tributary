"""JWT authentication middleware for Django Channels WebSocket connections.

Frontend connects as: ws://host/ws/chat/{id}/?token={jwt_access_token}
"""
from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def get_user_from_token(token_str):
    """Validate JWT access token and return the user, or AnonymousUser on failure."""
    if not token_str:
        return AnonymousUser()
    try:
        token = AccessToken(token_str)
        from apps.users.models import User
        return User.objects.get(id=token["user_id"])
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware:
    """Extract JWT from query string and attach user to scope."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        qs = parse_qs(scope.get("query_string", b"").decode())
        token = qs.get("token", [None])[0]
        scope["user"] = await get_user_from_token(token)
        return await self.inner(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(AuthMiddlewareStack(inner))
