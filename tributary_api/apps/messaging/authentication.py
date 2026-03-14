"""Custom JWT authentication that tracks last_seen in Redis."""
import logging

import redis
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)

LAST_SEEN_TTL = 300  # 5 minutes


def _get_redis():
    try:
        r = redis.Redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
        r.ping()
        return r
    except Exception:
        return None


class TrackingJWTAuthentication(JWTAuthentication):
    """Extends JWTAuthentication to set last_seen:{user_id} in Redis."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            user, token = result
            try:
                r = _get_redis()
                if r:
                    r.setex(f"last_seen:{user.id}", LAST_SEEN_TTL, "1")
            except Exception:
                logger.debug("Redis unavailable — skipping last_seen tracking")
        return result
