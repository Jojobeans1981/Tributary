"""Custom JWT authentication that tracks last_seen in Redis."""
import redis
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication

_redis = redis.Redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)

LAST_SEEN_TTL = 300  # 5 minutes


class TrackingJWTAuthentication(JWTAuthentication):
    """Extends JWTAuthentication to set last_seen:{user_id} in Redis."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            user, token = result
            _redis.setex(f"last_seen:{user.id}", LAST_SEEN_TTL, "1")
        return result
