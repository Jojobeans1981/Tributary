"""Celery tasks for user lifecycle — nudge emails."""
import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(name="users.send_incomplete_profile_nudge")
def send_incomplete_profile_nudge():
    """Daily 10:00 UTC — nudge users with incomplete profiles (registered > 7 days ago)."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.users.models import User

    cutoff = timezone.now() - timedelta(days=7)
    users = User.objects.filter(
        is_active=True,
        role="MEMBER",
        nudge_sent=False,
        date_joined__lte=cutoff,
    )

    nudged = 0
    for user in users:
        has_bio = bool(user.bio and user.bio.strip())
        has_selections = user.problem_selections.exists()

        if has_bio and has_selections:
            continue  # Profile is sufficiently complete

        _send_nudge_email(user, has_bio, has_selections)
        user.nudge_sent = True
        user.save(update_fields=["nudge_sent"])
        nudged += 1

    logger.info("Nudge task complete: %d users nudged.", nudged)
    return nudged


def _send_nudge_email(user, has_bio, has_selections):
    """Send a profile completion nudge email via SendGrid."""
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    sg_key = getattr(settings, "SENDGRID_API_KEY", None)
    if not sg_key:
        logger.warning("SENDGRID_API_KEY not configured — skipping nudge email.")
        return

    missing = []
    if not has_bio:
        missing.append("a bio")
    if not has_selections:
        missing.append("at least one problem statement selection")

    missing_text = " and ".join(missing)

    mail = Mail(
        from_email=settings.DEFAULT_FROM_EMAIL,
        to_emails=user.email,
        subject="Complete your Tributary profile",
        html_content=(
            f"<p>Hi {user.first_name},</p>"
            f"<p>Your Tributary profile is almost ready! To get matched with fellow "
            f"literacy professionals, please add {missing_text}.</p>"
            f'<p><a href="{settings.FRONTEND_URL}/profile">Complete Your Profile</a></p>'
            f"<p>— The Upstream Literacy Team</p>"
        ),
    )
    try:
        SendGridAPIClient(sg_key).send(mail)
    except Exception:
        logger.exception("Failed to send nudge email to %s", user.email)
