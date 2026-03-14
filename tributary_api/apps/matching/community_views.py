"""Community directory, channels, featured members, and match feedback APIs."""
from datetime import date

from django.db.models import Count, Q
from rest_framework.views import APIView

from apps.matching.models import (
    Connection,
    FeaturedMember,
    MatchFeedback,
    MatchScore,
    ProblemStatement,
    UserProblemSelection,
)
from apps.staff.permissions import IsUpstreamStaff
from apps.users.models import User
from apps.users.utils import err, ok


def _build_member_item(member, request_user, match_scores, connections, featured_ids):
    """Build a single member dict for community/channel responses."""
    # Match score
    score = match_scores.get(member.id, 0)

    # Connection status
    conn = connections.get(member.id)
    if conn is None:
        connection_status = "NONE"
    elif conn.status == Connection.ACCEPTED:
        connection_status = "ACCEPTED"
    elif conn.status == Connection.PENDING:
        if conn.requester_id == request_user.id:
            connection_status = "PENDING_SENT"
        else:
            connection_status = "PENDING_RECEIVED"
    else:
        connection_status = "NONE"

    # District
    district_data = None
    if member.district:
        district_data = {
            "name": member.district.name,
            "state": member.district.state,
            "locale_type": member.district.locale_type,
        }

    # Problem selections
    selections = [
        {"title": s.problem_statement.title, "category": s.problem_statement.category}
        for s in member.problem_selections.all()
    ]

    return {
        "id": str(member.id),
        "first_name": member.first_name,
        "last_name": member.last_name,
        "role": member.role,
        "bio_excerpt": (member.bio or "")[:100],
        "district": district_data,
        "problem_selections": selections,
        "match_score": score,
        "connection_status": connection_status,
        "is_featured": member.id in featured_ids,
    }


def _get_match_scores(user):
    """Get all match scores for a user as {other_id: total_score}."""
    scores = {}
    for ms in MatchScore.objects.filter(Q(user_a=user) | Q(user_b=user)):
        other_id = ms.user_b_id if ms.user_a_id == user.id else ms.user_a_id
        scores[other_id] = ms.total_score
    return scores


def _get_connections(user, member_ids):
    """Get connections for user with given member IDs."""
    connections = {}
    for conn in Connection.objects.filter(
        Q(requester=user, recipient_id__in=member_ids)
        | Q(recipient=user, requester_id__in=member_ids)
    ):
        other_id = conn.recipient_id if conn.requester_id == user.id else conn.requester_id
        connections[other_id] = conn
    return connections


def _get_active_featured_ids():
    """Get set of user IDs currently featured."""
    return set(
        FeaturedMember.objects.filter(
            Q(featured_until__isnull=True) | Q(featured_until__gte=date.today())
        ).values_list("user_id", flat=True)
    )


class CommunityListView(APIView):
    """GET /api/community/ — paginated member directory."""

    def get(self, request):
        user = request.user
        qs = User.objects.filter(
            is_active=True
        ).exclude(
            id=user.id
        ).select_related("district").prefetch_related(
            "problem_selections__problem_statement"
        )

        # Blocked exclusion
        blocked_ids = set()
        for conn in Connection.objects.filter(
            Q(requester=user, status=Connection.BLOCKED)
            | Q(recipient=user, status=Connection.BLOCKED)
        ):
            blocked_ids.add(conn.requester_id)
            blocked_ids.add(conn.recipient_id)
        blocked_ids.discard(user.id)
        if blocked_ids:
            qs = qs.exclude(id__in=blocked_ids)

        # Filters
        search = request.query_params.get("search", "")
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(district__name__icontains=search)
            )

        state = request.query_params.get("state")
        if state:
            qs = qs.filter(district__state=state)

        locale_type = request.query_params.get("locale_type")
        if locale_type:
            qs = qs.filter(district__locale_type=locale_type)

        problem_id = request.query_params.get("problem_statement_id")
        if problem_id:
            user_ids = UserProblemSelection.objects.filter(
                problem_statement_id=problem_id
            ).values_list("user_id", flat=True)
            qs = qs.filter(id__in=user_ids)

        # Sorting
        sort = request.query_params.get("sort", "match_score")
        if sort == "name":
            qs = qs.order_by("first_name", "last_name")
        elif sort == "joined":
            qs = qs.order_by("-date_joined")
        # match_score sorting done after fetching

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = 24
        members = list(qs)

        # Build lookups
        member_ids = [m.id for m in members]
        match_scores = _get_match_scores(user)
        connections = _get_connections(user, member_ids)
        featured_ids = _get_active_featured_ids()

        # Build results
        results = [
            _build_member_item(m, user, match_scores, connections, featured_ids)
            for m in members
        ]

        # Sort by match_score if requested (default)
        if sort == "match_score":
            results.sort(key=lambda x: x["match_score"], reverse=True)

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        page_results = results[start:end]

        return ok({
            "results": page_results,
            "total_count": len(results),
            "page": page,
            "has_more": end < len(results),
        })


class ChannelListView(APIView):
    """GET /api/channels/ — all active problem statements as channels."""

    def get(self, request):
        channels = (
            ProblemStatement.objects.filter(is_active=True)
            .annotate(
                member_count=Count(
                    "userproblemselection",
                    filter=Q(userproblemselection__user__is_active=True),
                )
            )
            .order_by("id")
        )
        data = [
            {
                "id": ch.id,
                "title": ch.title,
                "category": ch.category,
                "member_count": ch.member_count,
            }
            for ch in channels
        ]
        return ok(data)


class ChannelMembersView(APIView):
    """GET /api/channels/{id}/members/ — members with this selection."""

    def get(self, request, problem_id):
        user = request.user

        try:
            problem = ProblemStatement.objects.get(id=problem_id, is_active=True)
        except ProblemStatement.DoesNotExist:
            return err("NOT_FOUND", "Channel not found.", status=404)

        user_ids = UserProblemSelection.objects.filter(
            problem_statement=problem
        ).values_list("user_id", flat=True)

        members = User.objects.filter(
            id__in=user_ids, is_active=True
        ).exclude(
            id=user.id
        ).select_related("district").prefetch_related(
            "problem_selections__problem_statement"
        )

        member_ids = [m.id for m in members]
        match_scores = _get_match_scores(user)
        connections = _get_connections(user, member_ids)
        featured_ids = _get_active_featured_ids()

        results = [
            _build_member_item(m, user, match_scores, connections, featured_ids)
            for m in members
        ]
        results.sort(key=lambda x: x["match_score"], reverse=True)

        return ok({
            "channel": {"id": problem.id, "title": problem.title, "category": problem.category},
            "members": results,
        })


# ========== Featured Members (staff only) ==========


class FeaturedMemberListCreateView(APIView):
    """GET + POST /api/staff/featured/"""

    permission_classes = [IsUpstreamStaff]

    def get(self, request):
        featured = FeaturedMember.objects.filter(
            Q(featured_until__isnull=True) | Q(featured_until__gte=date.today())
        ).select_related("user", "featured_by")

        data = [
            {
                "id": str(f.id),
                "user_id": str(f.user_id),
                "user_name": f.user.get_full_name(),
                "featured_by": f.featured_by.get_full_name(),
                "featured_from": f.featured_from.isoformat(),
                "featured_until": f.featured_until.isoformat() if f.featured_until else None,
                "note": f.note,
            }
            for f in featured
        ]
        return ok(data)

    def post(self, request):
        user_id = request.data.get("user_id")
        note = request.data.get("note", "")
        featured_until = request.data.get("featured_until")

        if not user_id:
            return err("VALIDATION_ERROR", "user_id is required.")

        try:
            target = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return err("NOT_FOUND", "User not found.", status=404)

        # Check max 5 active
        active_count = FeaturedMember.objects.filter(
            Q(featured_until__isnull=True) | Q(featured_until__gte=date.today())
        ).count()
        if active_count >= 5:
            return err("LIMIT_EXCEEDED", "Maximum 5 active featured members allowed.")

        fm = FeaturedMember.objects.create(
            user=target,
            featured_by=request.user,
            note=note,
            featured_until=featured_until,
        )

        return ok({
            "id": str(fm.id),
            "user_id": str(fm.user_id),
            "user_name": target.get_full_name(),
        })


class FeaturedMemberDeleteView(APIView):
    """DELETE /api/staff/featured/{id}/"""

    permission_classes = [IsUpstreamStaff]

    def delete(self, request, featured_id):
        try:
            fm = FeaturedMember.objects.get(id=featured_id)
        except FeaturedMember.DoesNotExist:
            return err("NOT_FOUND", "Featured member not found.", status=404)

        fm.delete()
        return ok({"message": "Featured member removed."})


# ========== Match Feedback ==========


class MatchFeedbackCreateView(APIView):
    """POST /api/feedback/"""

    def post(self, request):
        connection_id = request.data.get("connection_id")
        rating = request.data.get("rating")
        feedback_text = request.data.get("feedback_text", "")

        if not connection_id or rating is None:
            return err("VALIDATION_ERROR", "connection_id and rating are required.")

        try:
            rating = int(rating)
        except (TypeError, ValueError):
            return err("VALIDATION_ERROR", "Rating must be an integer.")

        if rating < 1 or rating > 5:
            return err("VALIDATION_ERROR", "Rating must be between 1 and 5.")

        try:
            connection = Connection.objects.get(id=connection_id)
        except Connection.DoesNotExist:
            return err("NOT_FOUND", "Connection not found.", status=404)

        # User must be party to the connection
        if request.user.id not in (connection.requester_id, connection.recipient_id):
            return err("FORBIDDEN", "Not a party to this connection.", status=403)

        # Check duplicate
        if MatchFeedback.objects.filter(connection=connection).exists():
            return err("DUPLICATE", "Feedback already submitted for this connection.", status=409)

        fb = MatchFeedback.objects.create(
            connection=connection,
            rating=rating,
            feedback_text=feedback_text,
        )

        return ok({
            "id": str(fb.id),
            "connection_id": str(fb.connection_id),
            "rating": fb.rating,
            "feedback_text": fb.feedback_text,
        })


class MatchFeedbackListView(APIView):
    """GET /api/feedback/my/"""

    def get(self, request):
        feedbacks = MatchFeedback.objects.filter(
            Q(connection__requester=request.user)
            | Q(connection__recipient=request.user)
        ).select_related("connection")

        data = [
            {
                "id": str(fb.id),
                "connection_id": str(fb.connection_id),
                "rating": fb.rating,
                "feedback_text": fb.feedback_text,
                "submitted_at": fb.submitted_at.isoformat(),
            }
            for fb in feedbacks
        ]
        return ok(data)
