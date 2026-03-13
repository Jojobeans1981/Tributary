from django.db.models import Q
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.matching.models import (
    Connection,
    MatchScore,
    ProblemStatement,
    UserProblemSelection,
)
from apps.matching.serializers import (
    ConnectionSerializer,
    CreateConnectionSerializer,
    CreateSelectionSerializer,
    ProblemStatementSerializer,
    UpdateConnectionSerializer,
    UpdateSelectionSerializer,
    UserProblemSelectionSerializer,
)
from apps.matching.tasks import compute_user_match_scores
from apps.users.utils import err, ok


# ========== PROBLEM STATEMENTS ==========


class ProblemListView(APIView):
    """GET /api/problems/ — all active statements, ordered by id."""

    permission_classes = [AllowAny]

    def get(self, request):
        problems = ProblemStatement.objects.filter(is_active=True).order_by("id")
        serializer = ProblemStatementSerializer(problems, many=True)
        return ok(serializer.data)


# ========== USER PROBLEM SELECTIONS ==========


class SelectionListCreateView(APIView):
    """GET + POST /api/users/me/problem-selections/"""

    def get(self, request):
        selections = UserProblemSelection.objects.filter(
            user=request.user
        ).select_related("problem_statement")
        serializer = UserProblemSelectionSerializer(selections, many=True)
        return ok(serializer.data)

    def post(self, request):
        # Layer 3: View-level max-3 enforcement
        if UserProblemSelection.objects.filter(user=request.user).count() >= 3:
            return err(
                "SELECTION_LIMIT_EXCEEDED",
                "You have already selected 3 problem statements.",
            )

        serializer = CreateSelectionSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return err("VALIDATION_ERROR", serializer.errors)

        # Validate problem statement exists and is active
        try:
            problem = ProblemStatement.objects.get(
                pk=serializer.validated_data["problem_statement_id"],
                is_active=True,
            )
        except ProblemStatement.DoesNotExist:
            return err("VALIDATION_ERROR", "Problem statement not found.")

        # Check for duplicate selection
        if UserProblemSelection.objects.filter(
            user=request.user, problem_statement=problem
        ).exists():
            return err("VALIDATION_ERROR", "You have already selected this problem.")

        selection = UserProblemSelection.objects.create(
            user=request.user,
            problem_statement=problem,
            elaboration_text=serializer.validated_data.get("elaboration_text", ""),
        )

        # Trigger score recompute
        compute_user_match_scores.delay(str(request.user.id))

        result = UserProblemSelectionSerializer(selection).data
        return ok(result)


class SelectionDetailView(APIView):
    """DELETE + PATCH /api/users/me/problem-selections/{id}/"""

    def delete(self, request, selection_id):
        try:
            selection = UserProblemSelection.objects.get(
                pk=selection_id, user=request.user
            )
        except UserProblemSelection.DoesNotExist:
            return err("NOT_FOUND", "Selection not found.", status=404)

        selection.delete()

        # Trigger score recompute
        compute_user_match_scores.delay(str(request.user.id))

        return ok({"message": "Selection removed."})

    def patch(self, request, selection_id):
        try:
            selection = UserProblemSelection.objects.get(
                pk=selection_id, user=request.user
            )
        except UserProblemSelection.DoesNotExist:
            return err("NOT_FOUND", "Selection not found.", status=404)

        serializer = UpdateSelectionSerializer(data=request.data)
        if not serializer.is_valid():
            return err("VALIDATION_ERROR", serializer.errors)

        selection.elaboration_text = serializer.validated_data["elaboration_text"]
        selection.save(update_fields=["elaboration_text"])

        result = UserProblemSelectionSerializer(selection).data
        return ok(result)


# ========== MATCH FEED ==========


class MatchFeedView(APIView):
    """GET /api/matches/ — paginated, filtered, ranked match feed."""

    def get(self, request):
        user = request.user
        user_id = str(user.id)

        # Get blocked user IDs in both directions
        blocked_ids = set(
            Connection.objects.filter(
                Q(requester=user, status=Connection.BLOCKED)
                | Q(recipient=user, status=Connection.BLOCKED)
            ).values_list("requester_id", "recipient_id")
            .distinct()
            .values_list("requester_id", flat=True)
        ) | set(
            Connection.objects.filter(
                Q(requester=user, status=Connection.BLOCKED)
                | Q(recipient=user, status=Connection.BLOCKED)
            ).values_list("recipient_id", flat=True)
        )
        blocked_ids.discard(user.id)

        # Base queryset: scores involving this user, >= min_score
        min_score = int(request.query_params.get("min_score", 20))
        scores_qs = MatchScore.objects.filter(
            Q(user_a=user) | Q(user_b=user),
            total_score__gte=min_score,
        ).select_related(
            "user_a", "user_a__district",
            "user_b", "user_b__district",
        )

        # Exclude blocked users
        if blocked_ids:
            scores_qs = scores_qs.exclude(
                Q(user_a_id__in=blocked_ids) | Q(user_b_id__in=blocked_ids)
            )

        # Apply filters
        locale_type = request.query_params.get("locale_type")
        state = request.query_params.get("state")

        scores_qs = scores_qs.order_by("-total_score")

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = 20
        start = (page - 1) * page_size
        end = start + page_size

        scores = list(scores_qs[start:end])

        # Prefetch connections for all matched users
        matched_user_ids = []
        for s in scores:
            other = s.user_b if str(s.user_a_id) == user_id else s.user_a
            matched_user_ids.append(other.id)

        connections = {}
        for conn in Connection.objects.filter(
            Q(requester=user, recipient_id__in=matched_user_ids)
            | Q(recipient=user, requester_id__in=matched_user_ids)
        ):
            other_id = (
                conn.recipient_id
                if conn.requester_id == user.id
                else conn.requester_id
            )
            connections[other_id] = conn

        # Prefetch shared problem IDs
        user_pids = set(
            user.problem_selections.values_list(
                "problem_statement_id", flat=True
            )
        )

        # Build response
        results = []
        for s in scores:
            if str(s.user_a_id) == user_id:
                other = s.user_b
            else:
                other = s.user_a

            # Apply locale_type and state filters on the matched user's district
            if other.district:
                if locale_type and other.district.locale_type != locale_type:
                    continue
                if state and other.district.state != state:
                    continue

            # Get shared problems
            other_pids = set(
                other.problem_selections.values_list(
                    "problem_statement_id", flat=True
                )
            )
            shared_ids = list(user_pids & other_pids)
            shared_problems = ProblemStatement.objects.filter(
                id__in=shared_ids
            ).values("id", "title", "category")

            # Connection status
            conn = connections.get(other.id)
            if conn is None:
                connection_status = "NONE"
            elif conn.status == Connection.ACCEPTED:
                connection_status = "ACCEPTED"
            elif conn.status == Connection.PENDING:
                if conn.requester_id == user.id:
                    connection_status = "PENDING_SENT"
                else:
                    connection_status = "PENDING_RECEIVED"
            elif conn.status == Connection.BLOCKED:
                continue  # should already be excluded, but double-check
            else:
                connection_status = "NONE"

            district_data = None
            if other.district:
                district_data = {
                    "name": other.district.name,
                    "state": other.district.state,
                    "locale_type": other.district.locale_type,
                    "enrollment": other.district.enrollment,
                    "frl_pct": str(other.district.frl_pct),
                    "ell_pct": str(other.district.ell_pct),
                }

            results.append({
                "matched_user": {
                    "id": str(other.id),
                    "first_name": other.first_name,
                    "last_name": other.last_name,
                    "role": other.role,
                    "bio": other.bio,
                },
                "district": district_data,
                "shared_problems": list(shared_problems),
                "demographic_score": s.demographic_score,
                "problem_score": s.problem_score,
                "total_score": s.total_score,
                "connection_status": connection_status,
            })

        return ok({
            "results": results,
            "page": page,
            "has_more": len(scores) == page_size,
        })


# ========== CONNECTIONS ==========


class ConnectionListCreateView(APIView):
    """POST + GET /api/connections/"""

    def post(self, request):
        serializer = CreateConnectionSerializer(data=request.data)
        if not serializer.is_valid():
            return err("VALIDATION_ERROR", serializer.errors)

        recipient_id = serializer.validated_data["recipient_id"]

        # Can't connect to yourself
        if str(request.user.id) == str(recipient_id):
            return err("VALIDATION_ERROR", "You cannot connect with yourself.")

        # Check if blocked in either direction
        blocked = Connection.objects.filter(
            Q(
                requester=request.user,
                recipient_id=recipient_id,
                status=Connection.BLOCKED,
            )
            | Q(
                requester_id=recipient_id,
                recipient=request.user,
                status=Connection.BLOCKED,
            )
        ).exists()
        if blocked:
            return err(
                "CONNECTION_BLOCKED",
                "Cannot connect with this user.",
            )

        # Check if connection already exists (pending or accepted)
        existing = Connection.objects.filter(
            Q(requester=request.user, recipient_id=recipient_id)
            | Q(requester_id=recipient_id, recipient=request.user)
        ).filter(status__in=[Connection.PENDING, Connection.ACCEPTED]).exists()
        if existing:
            return err(
                "CONNECTION_EXISTS",
                "A connection already exists with this user.",
            )

        connection = Connection.objects.create(
            requester=request.user,
            recipient_id=recipient_id,
            intro_message=serializer.validated_data.get("intro_message", ""),
        )

        return ok(ConnectionSerializer(connection).data)

    def get(self, request):
        status_filter = request.query_params.get("status")
        qs = Connection.objects.filter(
            Q(requester=request.user) | Q(recipient=request.user)
        )
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        return ok(ConnectionSerializer(qs, many=True).data)


class ConnectionDetailView(APIView):
    """PATCH /api/connections/{id}/ — recipient only."""

    def patch(self, request, connection_id):
        try:
            connection = Connection.objects.get(pk=connection_id)
        except Connection.DoesNotExist:
            return err("NOT_FOUND", "Connection not found.", status=404)

        # Only recipient can accept/decline
        if connection.recipient_id != request.user.id:
            return err(
                "FORBIDDEN",
                "Only the recipient can update this connection.",
                status=403,
            )

        serializer = UpdateConnectionSerializer(data=request.data)
        if not serializer.is_valid():
            return err("VALIDATION_ERROR", serializer.errors)

        connection.status = serializer.validated_data["status"]
        connection.save(update_fields=["status", "updated_at"])

        # On accept, trigger score recompute for both users
        if connection.status == Connection.ACCEPTED:
            compute_user_match_scores.delay(str(connection.requester_id))
            compute_user_match_scores.delay(str(connection.recipient_id))

        return ok(ConnectionSerializer(connection).data)


class ConnectionBlockView(APIView):
    """POST /api/connections/{id}/block/ — either party can block."""

    def post(self, request, connection_id):
        try:
            connection = Connection.objects.get(pk=connection_id)
        except Connection.DoesNotExist:
            return err("NOT_FOUND", "Connection not found.", status=404)

        # Either party can block
        if request.user.id not in (
            connection.requester_id,
            connection.recipient_id,
        ):
            return err("FORBIDDEN", "Not a party to this connection.", status=403)

        connection.status = Connection.BLOCKED
        connection.save(update_fields=["status", "updated_at"])

        return ok({"message": "User blocked."})
