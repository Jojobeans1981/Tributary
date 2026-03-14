"""
Phase 4 integration tests — taxonomy CRUD, analytics dashboard.
"""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from allauth.account.models import EmailAddress

from apps.districts.models import District
from apps.matching.models import (
    Connection,
    MatchFeedback,
    MatchScore,
    ProblemStatement,
    UserProblemSelection,
)
from apps.messaging.models import Conversation, ConversationParticipant, Message
from apps.users.models import FerpaConsent, User


# ========== FIXTURES ==========


def _make_user(email, role="MEMBER", district=None, **kwargs):
    user = User.objects.create_user(
        email=email,
        password="TestPass123!",
        first_name=email.split("@")[0].title(),
        last_name="Tester",
        role=role,
        is_active=True,
        **kwargs,
    )
    EmailAddress.objects.create(user=user, email=email, primary=True, verified=True)
    FerpaConsent.objects.create(user=user, ip_address="127.0.0.1", consent_text_version="1.0")
    if district:
        user.district = district
        user.save(update_fields=["district"])
    return user


def _auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.fixture
def staff_user(db):
    return _make_user("staff@upstream.org", role="UPSTREAM_STAFF")


@pytest.fixture
def client_staff(staff_user):
    return _auth_client(staff_user)


@pytest.fixture
def member(db):
    return _make_user("member@example.com")


@pytest.fixture
def client_member(member):
    return _auth_client(member)


# ========== 1-4. TAXONOMY CRUD ==========


@pytest.mark.django_db
class TestTaxonomyCRUD:
    def test_create_statement(self, client_staff):
        """Test 1: POST /api/staff/taxonomy/ creates a problem statement."""
        res = client_staff.post(
            "/api/staff/taxonomy/",
            {
                "title": "Reading Fluency",
                "description": "Improving reading fluency across grades",
                "category": "Foundational Skills",
            },
            format="json",
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["title"] == "Reading Fluency"
        assert data["version"] == 1
        assert data["is_active"] is True

    def test_update_statement_bumps_version(self, client_staff):
        """Test 2: PATCH /api/staff/taxonomy/{id}/ updates and bumps version."""
        ps = ProblemStatement.objects.create(
            title="Old Title", description="Old", category="C", version=1, is_active=True,
        )
        res = client_staff.patch(
            f"/api/staff/taxonomy/{ps.id}/",
            {"title": "New Title"},
            format="json",
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["title"] == "New Title"
        assert data["version"] == 2

    def test_retire_statement(self, client_staff):
        """Test 3: POST /api/staff/taxonomy/{id}/retire/ sets is_active=False."""
        ps = ProblemStatement.objects.create(
            title="Retire Me", description="D", category="C", version=1, is_active=True,
        )
        res = client_staff.post(f"/api/staff/taxonomy/{ps.id}/retire/")
        assert res.status_code == 200
        ps.refresh_from_db()
        assert ps.is_active is False

    def test_retire_already_retired(self, client_staff):
        """Test 4: Retiring an already-retired statement returns error."""
        ps = ProblemStatement.objects.create(
            title="Already Retired", description="D", category="C",
            version=1, is_active=False,
        )
        res = client_staff.post(f"/api/staff/taxonomy/{ps.id}/retire/")
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "ALREADY_RETIRED"

    def test_member_cannot_access_taxonomy(self, client_member):
        """Test 5: Regular member gets 403 on taxonomy endpoints."""
        res = client_member.get("/api/staff/taxonomy/")
        assert res.status_code == 403


# ========== 6-8. ANALYTICS ==========


@pytest.mark.django_db
class TestAnalytics:
    def test_analytics_returns_summary(self, client_staff, staff_user):
        """Test 6: GET /api/staff/analytics/ returns summary and charts."""
        res = client_staff.get("/api/staff/analytics/")
        assert res.status_code == 200
        data = res.json()["data"]
        assert "summary" in data
        assert "charts" in data
        assert "total_members" in data["summary"]
        assert "member_growth" in data["charts"]

    def test_analytics_with_data(self, client_staff, staff_user):
        """Test 7: Analytics includes real data when records exist."""
        from django.core.cache import cache
        cache.clear()

        d = District.objects.create(
            nces_id="9900001", name="Test D", state="NY",
            locale_type="URBAN", enrollment=5000,
            frl_pct="50.00", ell_pct="15.00", data_vintage="2022-23",
        )
        alice = _make_user("an_alice@example.com", district=d)
        bob = _make_user("an_bob@example.com", district=d)

        conn = Connection.objects.create(
            requester=alice, recipient=bob, status=Connection.ACCEPTED,
        )
        MatchFeedback.objects.create(connection=conn, rating=4)

        res = client_staff.get("/api/staff/analytics/")
        data = res.json()["data"]
        # Should have at least the 2 members we created
        assert data["summary"]["total_members"] >= 2
        assert data["summary"]["avg_feedback_rating"] > 0

    def test_analytics_csv_export(self, client_staff, staff_user):
        """Test 8: GET /api/staff/analytics/export/ returns CSV."""
        res = client_staff.get("/api/staff/analytics/export/")
        assert res.status_code == 200
        assert res["Content-Type"] == "text/csv"
        assert "attachment" in res["Content-Disposition"]

    def test_member_cannot_access_analytics(self, client_member):
        """Test 9: Regular member gets 403 on analytics endpoints."""
        res = client_member.get("/api/staff/analytics/")
        assert res.status_code == 403
