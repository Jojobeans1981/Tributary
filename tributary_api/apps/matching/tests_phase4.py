"""
Phase 4 integration tests — community directory, channels, featured members,
match feedback, profile completion, and nudge/feedback-prompt tasks.
"""
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from allauth.account.models import EmailAddress

from apps.districts.models import District
from apps.matching.models import (
    Connection,
    FeaturedMember,
    MatchFeedback,
    MatchScore,
    ProblemStatement,
    UserProblemSelection,
)
from apps.messaging.models import Notification
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
def district_a(db):
    return District.objects.create(
        nces_id="0100001", name="Alpha District", state="OH",
        locale_type="URBAN", enrollment=10000, frl_pct="40.00",
        ell_pct="12.00", data_vintage="2022-23",
    )


@pytest.fixture
def district_b(db):
    return District.objects.create(
        nces_id="0100002", name="Beta District", state="CA",
        locale_type="RURAL", enrollment=3000, frl_pct="70.00",
        ell_pct="25.00", data_vintage="2022-23",
    )


@pytest.fixture
def problems(db):
    return [
        ProblemStatement.objects.create(
            title=f"Problem {i}", description=f"Desc {i}",
            category="Foundational Skills" if i <= 3 else "Curriculum & Instruction",
            is_active=True, version=1,
        )
        for i in range(1, 6)
    ]


@pytest.fixture
def alice(district_a):
    return _make_user("alice@example.com", district=district_a)


@pytest.fixture
def bob(district_b):
    return _make_user("bob@example.com", district=district_b)


@pytest.fixture
def staff_user(db):
    return _make_user("staff@upstream.org", role="UPSTREAM_STAFF")


@pytest.fixture
def client_alice(alice):
    return _auth_client(alice)


@pytest.fixture
def client_bob(bob):
    return _auth_client(bob)


@pytest.fixture
def client_staff(staff_user):
    return _auth_client(staff_user)


# ========== 1-3. COMMUNITY DIRECTORY ==========


@pytest.mark.django_db
class TestCommunityDirectory:
    def test_community_list_returns_members(self, client_alice, alice, bob):
        """Test 1: GET /api/community/ returns other active members."""
        res = client_alice.get("/api/community/")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["total_count"] >= 1
        ids = [m["id"] for m in data["results"]]
        assert str(bob.id) in ids
        assert str(alice.id) not in ids  # excludes self

    def test_community_search_filter(self, client_alice, alice, bob, district_b):
        """Test 2: search param filters by name/district."""
        res = client_alice.get("/api/community/?search=Beta")
        data = res.json()["data"]
        assert data["total_count"] >= 1
        assert all("Beta" in (m["district"]["name"] if m["district"] else "") for m in data["results"])

    def test_community_excludes_blocked(self, client_alice, alice, bob):
        """Test 3: Blocked users are excluded from community."""
        Connection.objects.create(
            requester=alice, recipient=bob, status=Connection.BLOCKED,
        )
        res = client_alice.get("/api/community/")
        ids = [m["id"] for m in res.json()["data"]["results"]]
        assert str(bob.id) not in ids


# ========== 4-5. CHANNELS ==========


@pytest.mark.django_db
class TestChannels:
    def test_channel_list(self, client_alice, alice, problems):
        """Test 4: GET /api/channels/ returns active problems as channels."""
        res = client_alice.get("/api/channels/")
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) >= 5  # at least the 5 we created (seed data may exist)
        assert all("member_count" in ch for ch in data)

    def test_channel_members(self, client_alice, alice, bob, problems):
        """Test 5: GET /api/channels/{id}/members/ returns members with that selection."""
        UserProblemSelection.objects.create(user=bob, problem_statement=problems[0])
        res = client_alice.get(f"/api/channels/{problems[0].id}/members/")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["channel"]["title"] == "Problem 1"
        assert len(data["members"]) >= 1
        assert data["members"][0]["id"] == str(bob.id)


# ========== 6-9. FEATURED MEMBERS (staff) ==========


@pytest.mark.django_db
class TestFeaturedMembers:
    def test_create_featured_member(self, client_staff, staff_user, alice):
        """Test 6: POST /api/staff/featured/ creates a featured member."""
        res = client_staff.post(
            "/api/staff/featured/",
            {"user_id": str(alice.id), "note": "Great contributor"},
            format="json",
        )
        assert res.status_code == 200
        assert res.json()["data"]["user_id"] == str(alice.id)

    def test_list_featured_members(self, client_staff, staff_user, alice):
        """Test 7: GET /api/staff/featured/ returns active featured members."""
        FeaturedMember.objects.create(user=alice, featured_by=staff_user)
        res = client_staff.get("/api/staff/featured/")
        assert res.status_code == 200
        assert len(res.json()["data"]) == 1

    def test_delete_featured_member(self, client_staff, staff_user, alice):
        """Test 8: DELETE /api/staff/featured/{id}/ removes featured status."""
        fm = FeaturedMember.objects.create(user=alice, featured_by=staff_user)
        res = client_staff.delete(f"/api/staff/featured/{fm.id}/")
        assert res.status_code == 200
        assert not FeaturedMember.objects.filter(id=fm.id).exists()

    def test_max_five_featured(self, client_staff, staff_user, district_a):
        """Test 9: Cannot create more than 5 active featured members."""
        for i in range(5):
            u = _make_user(f"feat{i}@example.com", district=district_a)
            FeaturedMember.objects.create(user=u, featured_by=staff_user)

        extra = _make_user("feat5@example.com", district=district_a)
        res = client_staff.post(
            "/api/staff/featured/",
            {"user_id": str(extra.id)},
            format="json",
        )
        assert res.status_code == 400
        assert "LIMIT_EXCEEDED" in res.json()["error"]["code"]


# ========== 10-13. MATCH FEEDBACK ==========


@pytest.mark.django_db
class TestMatchFeedback:
    def test_submit_feedback(self, client_alice, alice, bob):
        """Test 10: POST /api/feedback/ submits feedback for a connection."""
        conn = Connection.objects.create(
            requester=alice, recipient=bob, status=Connection.ACCEPTED,
        )
        res = client_alice.post(
            "/api/feedback/",
            {"connection_id": str(conn.id), "rating": 4, "feedback_text": "Helpful!"},
            format="json",
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["rating"] == 4
        assert data["feedback_text"] == "Helpful!"

    def test_duplicate_feedback_rejected(self, client_alice, alice, bob):
        """Test 11: Cannot submit feedback twice for the same connection."""
        conn = Connection.objects.create(
            requester=alice, recipient=bob, status=Connection.ACCEPTED,
        )
        MatchFeedback.objects.create(connection=conn, rating=3)
        res = client_alice.post(
            "/api/feedback/",
            {"connection_id": str(conn.id), "rating": 5},
            format="json",
        )
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "DUPLICATE"

    def test_non_party_feedback_rejected(self, client_alice, alice, bob, district_a):
        """Test 12: User not party to connection gets 403."""
        charlie = _make_user("charlie@example.com", district=district_a)
        conn = Connection.objects.create(
            requester=charlie, recipient=bob, status=Connection.ACCEPTED,
        )
        res = client_alice.post(
            "/api/feedback/",
            {"connection_id": str(conn.id), "rating": 3},
            format="json",
        )
        assert res.status_code == 403

    def test_list_my_feedback(self, client_alice, alice, bob):
        """Test 13: GET /api/feedback/my/ returns user's feedback."""
        conn = Connection.objects.create(
            requester=alice, recipient=bob, status=Connection.ACCEPTED,
        )
        MatchFeedback.objects.create(connection=conn, rating=5, feedback_text="Excellent")
        res = client_alice.get("/api/feedback/my/")
        assert res.status_code == 200
        assert len(res.json()["data"]) == 1
        assert res.json()["data"][0]["rating"] == 5


# ========== 14-15. PROFILE COMPLETION ==========


@pytest.mark.django_db
class TestProfileCompletion:
    def test_profile_completion_empty(self, client_alice, alice):
        """Test 14: Empty profile returns low completion pct."""
        alice.bio = ""
        alice.district = None
        alice.save()
        UserProblemSelection.objects.filter(user=alice).delete()
        res = client_alice.get("/api/users/me/")
        assert res.status_code == 200
        assert res.json()["data"]["profile_completion_pct"] == 0

    def test_profile_completion_full(self, client_alice, alice, problems):
        """Test 15: Full profile returns 100%."""
        alice.bio = "Literacy specialist with 10 years experience"
        alice.save()
        # district already set via fixture
        UserProblemSelection.objects.create(user=alice, problem_statement=problems[0])
        UserProblemSelection.objects.create(user=alice, problem_statement=problems[1])
        res = client_alice.get("/api/users/me/")
        assert res.status_code == 200
        assert res.json()["data"]["profile_completion_pct"] == 100


# ========== 16-17. NUDGE TASK ==========


@pytest.mark.django_db
class TestNudgeTask:
    @patch("apps.users.tasks._send_nudge_email")
    def test_nudge_targets_incomplete_profiles(self, mock_email):
        """Test 16: Nudge task targets users with incomplete profiles >7 days old."""
        from apps.users.tasks import send_incomplete_profile_nudge

        user = _make_user("nudge@example.com")
        # Backdate registration
        User.objects.filter(id=user.id).update(
            date_joined=timezone.now() - timedelta(days=10)
        )
        result = send_incomplete_profile_nudge()
        assert result >= 1
        user.refresh_from_db()
        assert user.nudge_sent is True
        mock_email.assert_called()

    @patch("apps.users.tasks._send_nudge_email")
    def test_nudge_skips_complete_profiles(self, mock_email):
        """Test 17: Nudge skips users with complete profiles."""
        from apps.users.tasks import send_incomplete_profile_nudge

        problems = [
            ProblemStatement.objects.create(
                title="P1", description="D", category="C", is_active=True, version=1,
            )
        ]
        user = _make_user("complete@example.com")
        user.bio = "I have a bio"
        user.save()
        UserProblemSelection.objects.create(user=user, problem_statement=problems[0])
        User.objects.filter(id=user.id).update(
            date_joined=timezone.now() - timedelta(days=10)
        )

        result = send_incomplete_profile_nudge()
        assert result == 0
        user.refresh_from_db()
        assert user.nudge_sent is False


# ========== 18-19. FEEDBACK PROMPT TASK ==========


@pytest.mark.django_db
class TestFeedbackPromptTask:
    @patch("apps.matching.tasks._send_feedback_email")
    def test_feedback_prompt_creates_notifications(self, mock_email):
        """Test 18: Feedback prompt task creates notifications for both parties."""
        from apps.matching.tasks import send_feedback_prompt

        alice = _make_user("fp_alice@example.com")
        bob = _make_user("fp_bob@example.com")
        conn = Connection.objects.create(
            requester=alice, recipient=bob, status=Connection.ACCEPTED,
        )

        send_feedback_prompt(str(conn.id))

        assert Notification.objects.filter(
            notification_type=Notification.FEEDBACK_PROMPT,
        ).count() == 2

    @patch("apps.matching.tasks._send_feedback_email")
    def test_feedback_prompt_skips_if_feedback_exists(self, mock_email):
        """Test 19: Feedback prompt skips if feedback already submitted."""
        from apps.matching.tasks import send_feedback_prompt

        alice = _make_user("fp2_alice@example.com")
        bob = _make_user("fp2_bob@example.com")
        conn = Connection.objects.create(
            requester=alice, recipient=bob, status=Connection.ACCEPTED,
        )
        MatchFeedback.objects.create(connection=conn, rating=4)

        send_feedback_prompt(str(conn.id))

        assert Notification.objects.filter(
            notification_type=Notification.FEEDBACK_PROMPT,
        ).count() == 0
        mock_email.assert_not_called()
