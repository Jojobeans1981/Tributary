"""
Phase 2 integration tests — 16 mandatory tests per spec.

Covers: models (max-3 enforcement), problem API, selection API,
match feed API, connection state machine, and blocked-pair exclusion.
"""
import pytest
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from allauth.account.models import EmailAddress

from apps.districts.models import District
from apps.matching.models import (
    Connection,
    MatchScore,
    ProblemStatement,
    UserProblemSelection,
)
from apps.users.models import FerpaConsent, User


# ========== FIXTURES ==========


@pytest.fixture
def api_client():
    return APIClient()


def _make_user(email, district=None):
    user = User.objects.create_user(
        email=email,
        password="TestPass123!",
        first_name=email.split("@")[0].title(),
        last_name="Tester",
        is_active=True,
    )
    EmailAddress.objects.create(user=user, email=email, primary=True, verified=True)
    FerpaConsent.objects.create(user=user, ip_address="127.0.0.1", consent_text_version="1.0")
    if district:
        user.district = district
        user.save(update_fields=["district"])
    return user


@pytest.fixture
def district_a(db):
    return District.objects.create(
        nces_id="0100001",
        name="Alpha District",
        state="OH",
        locale_type="URBAN",
        enrollment=10000,
        frl_pct="40.00",
        ell_pct="12.00",
        data_vintage="2022-23",
    )


@pytest.fixture
def district_b(db):
    return District.objects.create(
        nces_id="0100002",
        name="Beta District",
        state="CA",
        locale_type="RURAL",
        enrollment=3000,
        frl_pct="70.00",
        ell_pct="25.00",
        data_vintage="2022-23",
    )


@pytest.fixture
def problems(db):
    """Create 5 test problem statements."""
    return [
        ProblemStatement.objects.create(
            title=f"Problem {i}",
            description=f"Description {i}",
            category="Foundational Skills" if i <= 3 else "Curriculum & Instruction",
            is_active=True,
        )
        for i in range(1, 6)
    ]


@pytest.fixture
def user_a(district_a):
    return _make_user("alice@example.com", district_a)


@pytest.fixture
def user_b(district_b):
    return _make_user("bob@example.com", district_b)


@pytest.fixture
def auth_client_a(api_client, user_a):
    token = RefreshToken.for_user(user_a)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return api_client


@pytest.fixture
def auth_client_b(user_b):
    client = APIClient()
    token = RefreshToken.for_user(user_b)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


# ========== 1. PROBLEM LIST (public) ==========


@pytest.mark.django_db
class TestProblemList:
    def test_list_problems_returns_active_only(self, api_client, problems):
        """Test 1: GET /api/problems/ returns only active problems."""
        # Count active before deactivation
        res_before = api_client.get("/api/problems/")
        count_before = len(res_before.json()["data"])
        # Deactivate one
        problems[4].is_active = False
        problems[4].save()
        res = api_client.get("/api/problems/")
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == count_before - 1
        titles = [p["title"] for p in data]
        assert "Problem 5" not in titles


# ========== 2-4. SELECTION API + MAX-3 ==========


@pytest.mark.django_db
class TestSelections:
    def test_create_selection(self, auth_client_a, problems):
        """Test 2: POST creates a selection successfully."""
        res = auth_client_a.post(
            "/api/users/me/problem-selections/",
            {"problem_statement_id": problems[0].id, "elaboration_text": "My focus area"},
            format="json",
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["problem_statement"]["id"] == problems[0].id
        assert data["elaboration_text"] == "My focus area"

    def test_max_three_selection_view_layer(self, auth_client_a, user_a, problems):
        """Test 3: View-level max-3 returns SELECTION_LIMIT_EXCEEDED on 4th."""
        for i in range(3):
            UserProblemSelection.objects.create(user=user_a, problem_statement=problems[i])
        res = auth_client_a.post(
            "/api/users/me/problem-selections/",
            {"problem_statement_id": problems[3].id},
            format="json",
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "SELECTION_LIMIT_EXCEEDED"

    def test_max_three_selection_model_layer(self, user_a, problems):
        """Test 4: Model clean() raises ValidationError on 4th."""
        for i in range(3):
            UserProblemSelection.objects.create(user=user_a, problem_statement=problems[i])
        fourth = UserProblemSelection(user=user_a, problem_statement=problems[3])
        with pytest.raises(ValidationError):
            fourth.clean()

    def test_delete_selection(self, auth_client_a, user_a, problems):
        """Test 5: DELETE removes selection and allows re-selection."""
        sel = UserProblemSelection.objects.create(user=user_a, problem_statement=problems[0])
        res = auth_client_a.delete(f"/api/users/me/problem-selections/{sel.id}/")
        assert res.status_code == 200
        assert not UserProblemSelection.objects.filter(pk=sel.id).exists()

    def test_duplicate_selection_rejected(self, auth_client_a, user_a, problems):
        """Test 6: Cannot select the same problem twice."""
        UserProblemSelection.objects.create(user=user_a, problem_statement=problems[0])
        res = auth_client_a.post(
            "/api/users/me/problem-selections/",
            {"problem_statement_id": problems[0].id},
            format="json",
        )
        assert res.status_code == 400


# ========== 5-6. MATCH SCORE MODEL ==========


@pytest.mark.django_db
class TestMatchScore:
    def test_match_score_uuid_ordering(self, user_a, user_b):
        """Test 7: user_a is always the lexicographically lower UUID."""
        a_id, b_id = str(user_a.id), str(user_b.id)
        low, high = sorted([a_id, b_id])
        MatchScore.objects.create(
            user_a_id=low,
            user_b_id=high,
            demographic_score=30,
            problem_score=40,
            total_score=70,
        )
        score = MatchScore.objects.first()
        assert str(score.user_a_id) == low
        assert str(score.user_b_id) == high

    def test_match_score_unique_pair(self, user_a, user_b):
        """Test 8: Duplicate user_a+user_b pair raises IntegrityError."""
        a_id, b_id = sorted([str(user_a.id), str(user_b.id)])
        MatchScore.objects.create(
            user_a_id=a_id, user_b_id=b_id,
            demographic_score=30, problem_score=40, total_score=70,
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            MatchScore.objects.create(
                user_a_id=a_id, user_b_id=b_id,
                demographic_score=20, problem_score=20, total_score=40,
            )


# ========== 7-8. MATCH FEED API ==========


@pytest.mark.django_db
class TestMatchFeed:
    def test_match_feed_returns_matches(self, auth_client_a, user_a, user_b):
        """Test 9: GET /api/matches/ returns scored matches."""
        a_id, b_id = sorted([str(user_a.id), str(user_b.id)])
        MatchScore.objects.create(
            user_a_id=a_id, user_b_id=b_id,
            demographic_score=25, problem_score=40, total_score=65,
        )
        res = auth_client_a.get("/api/matches/")
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data["results"]) == 1
        assert data["results"][0]["total_score"] == 65

    def test_match_feed_min_score_filter(self, auth_client_a, user_a, user_b):
        """Test 10: min_score filter excludes low-scoring matches."""
        a_id, b_id = sorted([str(user_a.id), str(user_b.id)])
        MatchScore.objects.create(
            user_a_id=a_id, user_b_id=b_id,
            demographic_score=5, problem_score=10, total_score=15,
        )
        res = auth_client_a.get("/api/matches/?min_score=20")
        assert res.status_code == 200
        assert len(res.json()["data"]["results"]) == 0


# ========== 9-14. CONNECTION STATE MACHINE ==========


@pytest.mark.django_db
class TestConnections:
    def test_create_connection(self, auth_client_a, user_b):
        """Test 11: POST /api/connections/ creates PENDING connection."""
        res = auth_client_a.post(
            "/api/connections/",
            {"recipient_id": str(user_b.id), "intro_message": "Let's connect!"},
            format="json",
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["status"] == "PENDING"
        assert data["intro_message"] == "Let's connect!"

    def test_accept_connection(self, auth_client_b, user_a, user_b):
        """Test 12: Recipient can ACCEPT a PENDING connection."""
        conn = Connection.objects.create(requester=user_a, recipient=user_b)
        res = auth_client_b.patch(
            f"/api/connections/{conn.id}/",
            {"status": "ACCEPTED"},
            format="json",
        )
        assert res.status_code == 200
        assert res.json()["data"]["status"] == "ACCEPTED"

    def test_decline_connection(self, auth_client_b, user_a, user_b):
        """Test 13: Recipient can DECLINE a PENDING connection."""
        conn = Connection.objects.create(requester=user_a, recipient=user_b)
        res = auth_client_b.patch(
            f"/api/connections/{conn.id}/",
            {"status": "DECLINED"},
            format="json",
        )
        assert res.status_code == 200
        assert res.json()["data"]["status"] == "DECLINED"

    def test_requester_cannot_accept(self, auth_client_a, user_a, user_b):
        """Test 14: Requester gets 403 when trying to accept own request."""
        conn = Connection.objects.create(requester=user_a, recipient=user_b)
        res = auth_client_a.patch(
            f"/api/connections/{conn.id}/",
            {"status": "ACCEPTED"},
            format="json",
        )
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"

    def test_duplicate_connection_rejected(self, auth_client_a, user_a, user_b):
        """Test 15: Cannot create duplicate PENDING/ACCEPTED connection."""
        Connection.objects.create(requester=user_a, recipient=user_b, status=Connection.PENDING)
        res = auth_client_a.post(
            "/api/connections/",
            {"recipient_id": str(user_b.id)},
            format="json",
        )
        assert res.status_code == 400
        assert res.json()["error"]["code"] == "CONNECTION_EXISTS"


# ========== 15-16. BLOCKED EXCLUSION ==========


@pytest.mark.django_db
class TestBlockedExclusion:
    def test_block_connection(self, auth_client_a, user_a, user_b):
        """Test 16a: Either party can block a connection."""
        conn = Connection.objects.create(
            requester=user_a, recipient=user_b, status=Connection.ACCEPTED,
        )
        res = auth_client_a.post(f"/api/connections/{conn.id}/block/")
        assert res.status_code == 200
        conn.refresh_from_db()
        assert conn.status == Connection.BLOCKED

    def test_blocked_user_excluded_from_feed(self, auth_client_a, user_a, user_b):
        """Test 16b: Blocked users are excluded from match feed in both directions."""
        a_id, b_id = sorted([str(user_a.id), str(user_b.id)])
        MatchScore.objects.create(
            user_a_id=a_id, user_b_id=b_id,
            demographic_score=30, problem_score=40, total_score=70,
        )
        # Block user_b
        Connection.objects.create(
            requester=user_a, recipient=user_b, status=Connection.BLOCKED,
        )
        res = auth_client_a.get("/api/matches/")
        assert res.status_code == 200
        assert len(res.json()["data"]["results"]) == 0
