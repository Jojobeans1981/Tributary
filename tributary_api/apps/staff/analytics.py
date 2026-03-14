"""Staff analytics API — FR-10 metrics dashboard."""
import csv
import io
import logging
from datetime import date, timedelta

from celery import shared_task
from django.core.cache import cache
from django.db.models import Avg, Count, Q
from django.http import StreamingHttpResponse
from rest_framework.views import APIView

from apps.matching.models import (
    Connection,
    MatchFeedback,
    MatchScore,
    ProblemStatement,
    UserProblemSelection,
)
from apps.messaging.models import Message
from apps.staff.permissions import IsUpstreamStaff
from apps.users.models import User
from apps.users.utils import ok

logger = logging.getLogger(__name__)


@shared_task(name="staff.refresh_analytics_cache")
def refresh_analytics_cache():
    """Daily 01:00 UTC — pre-compute last-30-day analytics and cache."""
    date_to = date.today().isoformat()
    date_from = (date.today() - timedelta(days=30)).isoformat()
    data = compute_analytics(date_from, date_to)
    cache_key = f"analytics:{date_from}:{date_to}"
    cache.set(cache_key, data, timeout=86400)
    logger.info("Analytics cache refreshed for %s to %s", date_from, date_to)


def compute_analytics(date_from: str, date_to: str) -> dict:
    """Compute all FR-10 analytics metrics for a date range."""

    # Summary
    total_members = User.objects.filter(is_active=True, role="MEMBER").count()
    messages_sent = Message.objects.filter(
        sent_at__date__gte=date_from,
        sent_at__date__lte=date_to,
        is_deleted=False,
    ).count()

    total_connections = Connection.objects.filter(
        status__in=[Connection.ACCEPTED, Connection.DECLINED],
        updated_at__date__gte=date_from,
        updated_at__date__lte=date_to,
    ).count()
    accepted_connections = Connection.objects.filter(
        status=Connection.ACCEPTED,
        updated_at__date__gte=date_from,
        updated_at__date__lte=date_to,
    ).count()
    match_acceptance_rate = (
        round(accepted_connections / total_connections * 100, 1)
        if total_connections > 0
        else 0.0
    )

    avg_rating = MatchFeedback.objects.filter(
        submitted_at__date__gte=date_from,
        submitted_at__date__lte=date_to,
    ).aggregate(avg=Avg("rating"))["avg"]
    avg_feedback_rating = round(avg_rating, 2) if avg_rating else 0.0

    # Charts
    # 1. Member growth — cumulative count by date
    member_growth = []
    members_qs = User.objects.filter(
        is_active=True, role="MEMBER"
    ).order_by("date_joined")

    from_date = date.fromisoformat(date_from)
    to_date = date.fromisoformat(date_to)
    current = from_date
    while current <= to_date:
        count = User.objects.filter(
            is_active=True, role="MEMBER", date_joined__date__lte=current
        ).count()
        member_growth.append({"date": current.isoformat(), "cumulative_count": count})
        current += timedelta(days=1)

    # 2. Problem distribution
    problem_distribution = list(
        ProblemStatement.objects.filter(is_active=True)
        .annotate(
            selection_count=Count(
                "userproblemselection",
                filter=Q(userproblemselection__user__is_active=True),
            )
        )
        .values("id", "title", "selection_count")
        .order_by("-selection_count")
    )

    # 3. Message volume by date
    message_volume = []
    current = from_date
    while current <= to_date:
        count = Message.objects.filter(
            sent_at__date=current, is_deleted=False
        ).count()
        message_volume.append({"date": current.isoformat(), "count": count})
        current += timedelta(days=1)

    # 4. Top district pairs
    top_pairs = list(
        MatchScore.objects.filter(
            user_a__district__isnull=False,
            user_b__district__isnull=False,
        )
        .select_related("user_a__district", "user_b__district")
        .order_by("-total_score")[:20]
    )
    top_district_pairs = [
        {
            "district_a_name": s.user_a.district.name,
            "district_b_name": s.user_b.district.name,
            "total_score": s.total_score,
        }
        for s in top_pairs
    ]

    return {
        "summary": {
            "total_members": total_members,
            "messages_sent": messages_sent,
            "match_acceptance_rate": match_acceptance_rate,
            "avg_feedback_rating": avg_feedback_rating,
        },
        "charts": {
            "member_growth": member_growth,
            "problem_distribution": problem_distribution,
            "message_volume": message_volume,
            "top_district_pairs": top_district_pairs,
        },
    }


class StaffAnalyticsView(APIView):
    """GET /api/staff/analytics/ — cached 24hr analytics dashboard."""

    permission_classes = [IsUpstreamStaff]

    def get(self, request):
        date_from = request.query_params.get(
            "date_from",
            (date.today() - timedelta(days=30)).isoformat(),
        )
        date_to = request.query_params.get("date_to", date.today().isoformat())

        cache_key = f"analytics:{date_from}:{date_to}"
        data = cache.get(cache_key)
        if data is None:
            data = compute_analytics(date_from, date_to)
            cache.set(cache_key, data, timeout=86400)

        return ok(data)


class StaffAnalyticsExportView(APIView):
    """GET /api/staff/analytics/export/ — CSV download, always fresh."""

    permission_classes = [IsUpstreamStaff]

    def get(self, request):
        date_from = request.query_params.get(
            "date_from",
            (date.today() - timedelta(days=30)).isoformat(),
        )
        date_to = request.query_params.get("date_to", date.today().isoformat())

        data = compute_analytics(date_from, date_to)

        def generate_csv():
            output = io.StringIO()
            writer = csv.writer(output)

            # Summary section
            writer.writerow(["Section", "Metric", "Value"])
            for key, val in data["summary"].items():
                writer.writerow(["Summary", key, val])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

            # Member growth
            writer.writerow([])
            writer.writerow(["Date", "Cumulative Members"])
            for row in data["charts"]["member_growth"]:
                writer.writerow([row["date"], row["cumulative_count"]])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

            # Problem distribution
            writer.writerow([])
            writer.writerow(["Problem ID", "Title", "Selection Count"])
            for row in data["charts"]["problem_distribution"]:
                writer.writerow([row["id"], row["title"], row["selection_count"]])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

            # Message volume
            writer.writerow([])
            writer.writerow(["Date", "Message Count"])
            for row in data["charts"]["message_volume"]:
                writer.writerow([row["date"], row["count"]])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

            # Top district pairs
            writer.writerow([])
            writer.writerow(["District A", "District B", "Total Score"])
            for row in data["charts"]["top_district_pairs"]:
                writer.writerow([
                    row["district_a_name"],
                    row["district_b_name"],
                    row["total_score"],
                ])
            yield output.getvalue()

        response = StreamingHttpResponse(generate_csv(), content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="tributary-analytics-{date.today().isoformat()}.csv"'
        )
        return response
