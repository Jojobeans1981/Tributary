"""Celery tasks for email notifications."""
import logging

import redis
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

def _get_redis():
    try:
        r = redis.Redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
        r.ping()
        return r
    except Exception:
        return None


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_and_send_message_email(self, user_id: str, message_id: str):
    """Send email notification based on user's email_preference."""
    from apps.messaging.models import Message
    from apps.users.models import User

    try:
        user = User.objects.get(id=user_id, is_active=True)
        message = Message.objects.select_related("sender", "conversation").get(
            id=message_id
        )
    except (User.DoesNotExist, Message.DoesNotExist):
        return

    pref = user.email_preference

    if pref == "OFF":
        return

    if pref == "IMMEDIATE":
        # Skip if user was active in the last 5 minutes
        r = _get_redis()
        if r:
            last_seen_key = f"last_seen:{user_id}"
            if r.exists(last_seen_key):
                return

        _send_message_email(user, message)

    elif pref == "DAILY_DIGEST":
        # Push to Redis list for daily batch processing
        r = _get_redis()
        if r:
            digest_key = f"digest:{user_id}"
            r.rpush(
                digest_key,
                f"{message.sender.get_full_name()}: {message.body[:100]}",
            )


@shared_task
def send_daily_digest_emails():
    """Process daily digest for all users with queued messages."""
    from apps.users.models import User

    users = User.objects.filter(
        email_preference="DAILY_DIGEST", is_active=True
    )
    r = _get_redis()
    if not r:
        logger.warning("Redis unavailable — skipping daily digest.")
        return

    for user in users:
        digest_key = f"digest:{user.id}"
        items = r.lrange(digest_key, 0, -1)
        if not items:
            continue
        r.delete(digest_key)
        _send_digest_email(user, items)


def _send_message_email(user, message):
    """Send an immediate message notification email via SendGrid."""
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    sg_key = getattr(settings, "SENDGRID_API_KEY", None)
    if not sg_key:
        logger.warning("SENDGRID_API_KEY not configured — skipping email.")
        return

    mail = Mail(
        from_email=settings.DEFAULT_FROM_EMAIL,
        to_emails=user.email,
        subject="New message on Tributary",
        html_content=(
            f"<p>Hi {user.first_name},</p>"
            f"<p><strong>{message.sender.get_full_name()}</strong> sent you a message:</p>"
            f"<blockquote>{message.body[:200]}</blockquote>"
            f'<p><a href="{settings.FRONTEND_URL}/inbox">Open Inbox</a></p>'
        ),
    )
    try:
        SendGridAPIClient(sg_key).send(mail)
    except Exception:
        logger.exception("Failed to send message email to %s", user.email)


def _send_digest_email(user, items):
    """Send a daily digest email with all queued messages."""
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    sg_key = getattr(settings, "SENDGRID_API_KEY", None)
    if not sg_key:
        logger.warning("SENDGRID_API_KEY not configured — skipping digest.")
        return

    preview_lines = "".join(f"<li>{item}</li>" for item in items[:20])
    mail = Mail(
        from_email=settings.DEFAULT_FROM_EMAIL,
        to_emails=user.email,
        subject=f"Tributary — {len(items)} new message(s) today",
        html_content=(
            f"<p>Hi {user.first_name},</p>"
            f"<p>You have {len(items)} new message(s):</p>"
            f"<ul>{preview_lines}</ul>"
            f'<p><a href="{settings.FRONTEND_URL}/inbox">Open Inbox</a></p>'
        ),
    )
    try:
        SendGridAPIClient(sg_key).send(mail)
    except Exception:
        logger.exception("Failed to send digest email to %s", user.email)
