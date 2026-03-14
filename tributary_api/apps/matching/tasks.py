import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(name="matching.send_feedback_prompt")
def send_feedback_prompt(connection_id: str):
    """Triggered 7 days after first message — prompt both parties for feedback."""
    from apps.matching.models import Connection, MatchFeedback
    from apps.messaging.models import Notification
    from apps.users.models import User

    try:
        connection = Connection.objects.get(id=connection_id)
    except Connection.DoesNotExist:
        return

    # Only prompt for accepted connections
    if connection.status != Connection.ACCEPTED:
        return

    # Skip if feedback already submitted
    if MatchFeedback.objects.filter(connection=connection).exists():
        return

    # Create FEEDBACK_PROMPT notifications for both parties
    for user_id in [connection.requester_id, connection.recipient_id]:
        Notification.objects.create(
            user_id=user_id,
            notification_type=Notification.FEEDBACK_PROMPT,
            reference_id=connection.id,
            reference_type="Connection",
        )

    # Send email if preference != OFF
    for user_id in [connection.requester_id, connection.recipient_id]:
        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            continue
        if user.email_preference == "OFF":
            continue
        _send_feedback_email(user, connection)

    logger.info("Feedback prompt sent for connection %s", connection_id)


def _send_feedback_email(user, connection):
    """Send feedback prompt email via SendGrid."""
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    sg_key = getattr(settings, "SENDGRID_API_KEY", None)
    if not sg_key:
        logger.warning("SENDGRID_API_KEY not configured — skipping feedback email.")
        return

    # Determine the other party's name
    if user.id == connection.requester_id:
        other = connection.recipient
    else:
        other = connection.requester

    mail = Mail(
        from_email=settings.DEFAULT_FROM_EMAIL,
        to_emails=user.email,
        subject="How is your connection going?",
        html_content=(
            f"<p>Hi {user.first_name},</p>"
            f"<p>It's been a week since you connected with "
            f"<strong>{other.get_full_name()}</strong>. "
            f"We'd love to hear how it's going!</p>"
            f'<p><a href="{settings.FRONTEND_URL}/matches">Share Your Feedback</a></p>'
            f"<p>— The Upstream Literacy Team</p>"
        ),
    )
    try:
        SendGridAPIClient(sg_key).send(mail)
    except Exception:
        logger.exception("Failed to send feedback email to %s", user.email)


@shared_task(name="matching.compute_all_match_scores")
def compute_all_match_scores():
    """Nightly full recompute of all match scores (02:00 UTC)."""
    from apps.matching.models import MatchScore
    from apps.matching.scoring import (
        DistrictProfile,
        UserMatchProfile,
        compute_match_score,
    )
    from apps.users.models import User

    users = (
        User.objects.filter(is_active=True, district__isnull=False)
        .select_related("district")
        .prefetch_related("problem_selections")
    )

    profiles = []
    for u in users:
        pids = list(
            u.problem_selections.values_list("problem_statement_id", flat=True)
        )
        if not pids:
            continue
        profiles.append(
            UserMatchProfile(
                user_id=str(u.id),
                district=DistrictProfile(
                    locale_type=u.district.locale_type,
                    enrollment=u.district.enrollment,
                    frl_pct=float(u.district.frl_pct),
                    ell_pct=float(u.district.ell_pct),
                ),
                problem_ids=pids,
            )
        )

    for i in range(len(profiles)):
        for j in range(i + 1, len(profiles)):
            r = compute_match_score(profiles[i], profiles[j])
            MatchScore.objects.update_or_create(
                user_a_id=r.user_a_id,
                user_b_id=r.user_b_id,
                defaults={
                    "demographic_score": r.demographic_score,
                    "problem_score": r.problem_score,
                    "total_score": r.total_score,
                },
            )


@shared_task(name="matching.compute_user_match_scores")
def compute_user_match_scores(user_id: str):
    """Triggered on selection change — recompute scores for one user."""
    from apps.matching.models import MatchScore
    from apps.matching.scoring import (
        DistrictProfile,
        UserMatchProfile,
        compute_match_score,
    )
    from apps.users.models import User

    try:
        user = User.objects.select_related("district").get(
            pk=user_id, is_active=True, district__isnull=False
        )
    except User.DoesNotExist:
        return

    user_pids = list(
        user.problem_selections.values_list("problem_statement_id", flat=True)
    )
    if not user_pids:
        return

    user_profile = UserMatchProfile(
        user_id=str(user.id),
        district=DistrictProfile(
            locale_type=user.district.locale_type,
            enrollment=user.district.enrollment,
            frl_pct=float(user.district.frl_pct),
            ell_pct=float(user.district.ell_pct),
        ),
        problem_ids=user_pids,
    )

    others = (
        User.objects.filter(is_active=True, district__isnull=False)
        .exclude(pk=user_id)
        .select_related("district")
        .prefetch_related("problem_selections")
    )

    for other in others:
        other_pids = list(
            other.problem_selections.values_list(
                "problem_statement_id", flat=True
            )
        )
        if not other_pids:
            continue

        other_profile = UserMatchProfile(
            user_id=str(other.id),
            district=DistrictProfile(
                locale_type=other.district.locale_type,
                enrollment=other.district.enrollment,
                frl_pct=float(other.district.frl_pct),
                ell_pct=float(other.district.ell_pct),
            ),
            problem_ids=other_pids,
        )

        r = compute_match_score(user_profile, other_profile)
        MatchScore.objects.update_or_create(
            user_a_id=r.user_a_id,
            user_b_id=r.user_b_id,
            defaults={
                "demographic_score": r.demographic_score,
                "problem_score": r.problem_score,
                "total_score": r.total_score,
            },
        )
