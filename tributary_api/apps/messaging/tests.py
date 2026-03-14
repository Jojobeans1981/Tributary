"""
Phase 3 integration tests — 21 mandatory tests per spec.

Covers: conversation CRUD, message send/pagination, deleted-message masking,
notifications, mark-read, blocked-user exclusion, staff join/delete/DM/broadcast/suspend,
audit trail, and rate limiting.
"""
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from allauth.account.models import EmailAddress

from apps.matching.models import Connection
from apps.messaging.models import (
    Conversation,
    ConversationParticipant,
    Message,
    Notification,
    StaffAction,
)
from apps.users.models import FerpaConsent, User


# ========== FIXTURES ==========


def _make_user(email, role="MEMBER", **kwargs):
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
    FerpaConsent.objects.create(
        user=user, ip_address="127.0.0.1", consent_text_version="1.0"
    )
    return user


def _auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


def _create_convo(user_a, user_b, staff_initiated=False):
    convo = Conversation.objects.create(is_staff_initiated=staff_initiated)
    ConversationParticipant.objects.create(conversation=convo, user=user_a)
    ConversationParticipant.objects.create(conversation=convo, user=user_b)
    return convo


@pytest.fixture
def alice(db):
    return _make_user("alice@example.com")


@pytest.fixture
def bob(db):
    return _make_user("bob@example.com")


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


# ========== 1-3. CONVERSATION CRUD ==========


@pytest.mark.django_db
class TestConversationCRUD:
    def test_create_conversation_with_accepted_connection(
        self, client_alice, alice, bob
    ):
        """Test 1: POST /api/conversations/ succeeds with ACCEPTED connection."""
        Connection.objects.create(
            requester=alice, recipient=bob, status=Connection.ACCEPTED
        )
        res = client_alice.post(
            "/api/conversations/",
            {"participant_id": str(bob.id)},
            format="json",
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert len(data["data"]["participants"]) == 2

    def test_create_conversation_rejected_without_connection(
        self, client_alice, bob
    ):
        """Test 2: POST /api/conversations/ fails without ACCEPTED connection."""
        res = client_alice.post(
            "/api/conversations/",
            {"participant_id": str(bob.id)},
            format="json",
        )
        assert res.status_code == 400
        assert res.json()["success"] is False

    def test_create_conversation_rejected_blocked_user(
        self, client_alice, alice, bob
    ):
        """Test 3: POST /api/conversations/ fails with BLOCKED connection."""
        Connection.objects.create(
            requester=alice, recipient=bob, status=Connection.BLOCKED
        )
        res = client_alice.post(
            "/api/conversations/",
            {"participant_id": str(bob.id)},
            format="json",
        )
        assert res.status_code == 400
        assert "blocked" in res.json()["error"]["message"].lower()

    def test_list_conversations(self, client_alice, alice, bob):
        """Test 4: GET /api/conversations/ returns my conversations."""
        _create_convo(alice, bob)
        res = client_alice.get("/api/conversations/")
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 1
        assert "last_message_preview" in data[0]
        assert "unread_count" in data[0]


# ========== 4-7. MESSAGES ==========


@pytest.mark.django_db
class TestMessages:
    @patch("apps.messaging.tasks.check_and_send_message_email")
    def test_send_message(self, mock_email, client_alice, alice, bob):
        """Test 5: POST message creates message + notification."""
        convo = _create_convo(alice, bob)
        res = client_alice.post(
            f"/api/conversations/{convo.id}/messages/",
            {"body": "Hello Bob!"},
            format="json",
        )
        assert res.status_code == 200
        assert res.json()["data"]["body"] == "Hello Bob!"
        assert Notification.objects.filter(
            user=bob, notification_type=Notification.NEW_MESSAGE
        ).exists()

    def test_get_messages_paginated(self, client_alice, alice, bob):
        """Test 6: GET messages returns cursor-paginated results (50/page)."""
        convo = _create_convo(alice, bob)
        for i in range(55):
            Message.objects.create(
                conversation=convo, sender=alice, body=f"Msg {i}"
            )
        res = client_alice.get(f"/api/conversations/{convo.id}/messages/")
        assert res.status_code == 200
        assert len(res.json()["data"]) == 50

    def test_non_participant_cannot_read_messages(self, client_bob, alice, bob):
        """Test 7: Non-participant gets 403."""
        other = _make_user("charlie@example.com")
        convo = _create_convo(alice, other)
        res = client_bob.get(f"/api/conversations/{convo.id}/messages/")
        assert res.status_code == 400 or res.status_code == 403
        # View returns err() with FORBIDDEN code
        assert res.json()["success"] is False

    def test_deleted_message_masked(self, client_alice, alice, bob):
        """Test 8: Deleted messages show masked text."""
        convo = _create_convo(alice, bob)
        msg = Message.objects.create(
            conversation=convo, sender=bob, body="Secret message"
        )
        msg.is_deleted = True
        msg.save()

        res = client_alice.get(f"/api/conversations/{convo.id}/messages/")
        body = res.json()["data"][0]["body"]
        assert body == "[This message was removed by a moderator]"


# ========== 8-9. NOTIFICATIONS & MARK READ ==========


@pytest.mark.django_db
class TestNotifications:
    def test_list_notifications(self, client_alice, alice):
        """Test 9: GET /api/notifications/ returns user's notifications."""
        Notification.objects.create(
            user=alice,
            notification_type=Notification.NEW_MESSAGE,
            reference_type="Conversation",
        )
        res = client_alice.get("/api/notifications/")
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 1
        assert "human_message" in data[0]

    def test_mark_all_read(self, client_alice, alice):
        """Test 10: PATCH /api/notifications/read-all/ marks all as read."""
        for _ in range(3):
            Notification.objects.create(
                user=alice,
                notification_type=Notification.CONNECTION_REQUEST,
            )
        res = client_alice.patch("/api/notifications/read-all/")
        assert res.status_code == 200
        assert Notification.objects.filter(user=alice, is_read=False).count() == 0

    def test_mark_conversation_read(self, client_alice, alice, bob):
        """Test 11: PATCH /api/conversations/{id}/read/ updates last_read_at."""
        convo = _create_convo(alice, bob)
        res = client_alice.patch(f"/api/conversations/{convo.id}/read/")
        assert res.status_code == 200
        participant = ConversationParticipant.objects.get(
            user=alice, conversation=convo
        )
        assert participant.last_read_at is not None


# ========== 10-11. STAFF CONVERSATION JOIN & MESSAGE DELETE ==========


@pytest.mark.django_db
class TestStaffModeration:
    def test_staff_join_conversation(self, client_staff, staff_user, alice, bob):
        """Test 12: Staff can join any conversation + system message + audit."""
        convo = _create_convo(alice, bob)
        res = client_staff.post(f"/api/staff/conversations/{convo.id}/join/")
        assert res.status_code == 200

        # System message created
        sys_msg = Message.objects.filter(
            conversation=convo, system_message=True
        ).first()
        assert sys_msg is not None
        assert "staff" in sys_msg.body.lower()

        # Audit log
        assert StaffAction.objects.filter(
            staff=staff_user,
            action_type=StaffAction.CONVERSATION_JOINED,
        ).exists()

        # Notifications
        assert Notification.objects.filter(
            notification_type=Notification.STAFF_JOINED
        ).count() == 2  # alice + bob

    def test_staff_delete_message(self, client_staff, staff_user, alice, bob):
        """Test 13: Staff can soft-delete a message + audit trail."""
        convo = _create_convo(alice, bob)
        msg = Message.objects.create(
            conversation=convo, sender=alice, body="Bad content"
        )

        res = client_staff.delete(f"/api/staff/messages/{msg.id}/")
        assert res.status_code == 204

        msg.refresh_from_db()
        assert msg.is_deleted is True
        assert msg.deleted_by == staff_user

        assert StaffAction.objects.filter(
            staff=staff_user,
            action_type=StaffAction.MESSAGE_DELETED,
            target_id=msg.id,
        ).exists()

    def test_staff_dm_member(self, client_staff, staff_user, alice):
        """Test 14: Staff can DM any member (creates staff-initiated convo)."""
        res = client_staff.post(
            "/api/staff/messages/",
            {"recipient_id": str(alice.id), "body": "Hello from staff"},
            format="json",
        )
        assert res.status_code == 200
        assert res.json()["data"]["body"] == "Hello from staff"

        # Conversation is staff-initiated
        convo = Conversation.objects.filter(is_staff_initiated=True).first()
        assert convo is not None

        # Audit
        assert StaffAction.objects.filter(
            action_type=StaffAction.MESSAGE_SENT_TO_MEMBER
        ).exists()


# ========== 12-13. STAFF BROADCAST & RATE LIMIT ==========


@pytest.mark.django_db
class TestStaffBroadcast:
    @patch("apps.staff.views._redis")
    def test_broadcast_creates_per_member_convos(
        self, mock_redis, client_staff, staff_user, alice, bob
    ):
        """Test 15: Broadcast creates one conversation per recipient."""
        mock_redis.get.return_value = None
        mock_redis.pipeline.return_value = mock_redis
        mock_redis.incr.return_value = mock_redis
        mock_redis.expire.return_value = mock_redis
        mock_redis.execute.return_value = None

        res = client_staff.post(
            "/api/staff/broadcast/",
            {
                "body": "Important announcement",
                "recipient_ids": [str(alice.id), str(bob.id)],
            },
            format="json",
        )
        assert res.status_code == 200
        assert res.json()["data"]["recipient_count"] == 2
        assert Conversation.objects.filter(is_staff_initiated=True).count() == 2

        assert StaffAction.objects.filter(
            action_type=StaffAction.BROADCAST_SENT
        ).exists()

    @patch("apps.staff.views._redis")
    def test_broadcast_rate_limit(self, mock_redis, client_staff, staff_user):
        """Test 16: Broadcast returns 429 after 3 broadcasts in 24h."""
        mock_redis.get.return_value = "3"

        res = client_staff.post(
            "/api/staff/broadcast/",
            {"body": "Spam", "recipient_ids": [str(staff_user.id)]},
            format="json",
        )
        assert res.status_code == 429
        assert "limit" in res.json()["error"]["message"].lower()


# ========== 14. STAFF SUSPEND USER ==========


@pytest.mark.django_db
class TestStaffSuspend:
    def test_suspend_member(self, client_staff, staff_user, alice):
        """Test 17: Staff can suspend a member + audit."""
        res = client_staff.post(f"/api/staff/users/{alice.id}/suspend/")
        assert res.status_code == 200
        alice.refresh_from_db()
        assert alice.is_active is False

        assert StaffAction.objects.filter(
            staff=staff_user,
            action_type=StaffAction.MEMBER_SUSPENDED,
            target_id=alice.id,
        ).exists()

    def test_cannot_suspend_staff(self, client_staff, staff_user):
        """Test 18: Cannot suspend another staff user."""
        other_staff = _make_user("admin@upstream.org", role="PLATFORM_ADMIN")
        res = client_staff.post(f"/api/staff/users/{other_staff.id}/suspend/")
        assert res.status_code == 403

    def test_member_cannot_access_staff_endpoints(self, client_alice, alice, bob):
        """Test 19: Regular member gets 403 on staff endpoints."""
        res = client_alice.get("/api/staff/conversations/")
        assert res.status_code == 403


# ========== 15. STAFF CREATES CONVERSATION WITHOUT CONNECTION ==========


@pytest.mark.django_db
class TestStaffBypassConnection:
    def test_staff_can_create_conversation_without_connection(
        self, client_staff, staff_user, alice
    ):
        """Test 20: Staff can start conversation without ACCEPTED connection."""
        res = client_staff.post(
            "/api/conversations/",
            {"participant_id": str(alice.id)},
            format="json",
        )
        assert res.status_code == 200
        assert res.json()["success"] is True


# ========== 16. CONVERSATION RETURNS EXISTING ==========


@pytest.mark.django_db
class TestConversationDedup:
    def test_create_returns_existing_conversation(
        self, client_alice, alice, bob
    ):
        """Test 21: Creating convo with same user returns existing convo."""
        Connection.objects.create(
            requester=alice, recipient=bob, status=Connection.ACCEPTED
        )
        res1 = client_alice.post(
            "/api/conversations/",
            {"participant_id": str(bob.id)},
            format="json",
        )
        convo_id_1 = res1.json()["data"]["id"]

        res2 = client_alice.post(
            "/api/conversations/",
            {"participant_id": str(bob.id)},
            format="json",
        )
        convo_id_2 = res2.json()["data"]["id"]

        assert convo_id_1 == convo_id_2
