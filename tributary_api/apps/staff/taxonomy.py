"""Staff taxonomy management API — problem statement CRUD."""
from django.db.models import Count, Q
from rest_framework.views import APIView

from apps.matching.models import ProblemStatement, UserProblemSelection
from apps.staff.permissions import IsUpstreamStaff
from apps.users.utils import err, ok


class TaxonomyListCreateView(APIView):
    """GET + POST /api/staff/taxonomy/"""

    permission_classes = [IsUpstreamStaff]

    def get(self, request):
        statements = ProblemStatement.objects.annotate(
            member_count=Count(
                "userproblemselection",
                filter=Q(userproblemselection__user__is_active=True),
            )
        ).order_by("id")

        data = [
            {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "category": s.category,
                "is_active": s.is_active,
                "version": s.version,
                "member_count": s.member_count,
            }
            for s in statements
        ]
        return ok(data)

    def post(self, request):
        title = request.data.get("title", "").strip()
        description = request.data.get("description", "").strip()
        category = request.data.get("category", "").strip()

        if not title or not description or not category:
            return err("VALIDATION_ERROR", "title, description, and category are required.")

        statement = ProblemStatement.objects.create(
            title=title,
            description=description,
            category=category,
            version=1,
            is_active=True,
        )

        return ok({
            "id": statement.id,
            "title": statement.title,
            "description": statement.description,
            "category": statement.category,
            "version": statement.version,
            "is_active": statement.is_active,
        })


class TaxonomyDetailView(APIView):
    """PATCH /api/staff/taxonomy/{id}/"""

    permission_classes = [IsUpstreamStaff]

    def patch(self, request, statement_id):
        try:
            statement = ProblemStatement.objects.get(id=statement_id)
        except ProblemStatement.DoesNotExist:
            return err("NOT_FOUND", "Statement not found.", status=404)

        title = request.data.get("title")
        description = request.data.get("description")
        category = request.data.get("category")

        if title:
            statement.title = title.strip()
        if description:
            statement.description = description.strip()
        if category:
            statement.category = category.strip()

        statement.version += 1
        statement.save()

        return ok({
            "id": statement.id,
            "title": statement.title,
            "description": statement.description,
            "category": statement.category,
            "version": statement.version,
            "is_active": statement.is_active,
        })


class TaxonomyRetireView(APIView):
    """POST /api/staff/taxonomy/{id}/retire/"""

    permission_classes = [IsUpstreamStaff]

    def post(self, request, statement_id):
        try:
            statement = ProblemStatement.objects.get(id=statement_id)
        except ProblemStatement.DoesNotExist:
            return err("NOT_FOUND", "Statement not found.", status=404)

        if not statement.is_active:
            return err("ALREADY_RETIRED", "Statement is already retired.")

        member_count = UserProblemSelection.objects.filter(
            problem_statement=statement, user__is_active=True
        ).count()

        statement.is_active = False
        statement.save(update_fields=["is_active"])

        return ok({
            "member_count": member_count,
            "message": f"Statement retired. {member_count} members retain their selection.",
        })
