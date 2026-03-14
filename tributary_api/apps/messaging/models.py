import uuid

from django.conf import settings
from django.db import models


class Conversation(models.Model):
    """Threaded conversation between connected members."""

    ASYNC = "ASYNC"
    REALTIME = "REALTIME"
    TYPE_CHOICES = [
        (ASYNC, "Async"),
        (REALTIME, "Realtime"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation_type = models.CharField(
        max_length=10, choices=TYPE_CHOICES, default=ASYNC
    )
    is_staff_initiated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Conversation {self.id}"


class ConversationParticipant(models.Model):
    """Tracks which users are in a conversation and their read state."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversation_participants",
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("user", "conversation")]

    def __str__(self):
        return f"{self.user} in {self.conversation_id}"


class Message(models.Model):
    """A single message in a conversation. Soft-delete only."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    body = models.TextField(max_length=5000)
    attachment_url = models.URLField(max_length=500, null=True, blank=True)
    attachment_type = models.CharField(max_length=10, null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_messages",
    )
    system_message = models.BooleanField(default=False)

    class Meta:
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["conversation", "-sent_at"]),
            models.Index(fields=["conversation", "is_deleted"]),
        ]

    def __str__(self):
        return f"Message {self.id} by {self.sender_id}"


class Notification(models.Model):
    """In-app notification for messages, connections, and staff actions."""

    NEW_MESSAGE = "NEW_MESSAGE"
    CONNECTION_REQUEST = "CONNECTION_REQUEST"
    CONNECTION_ACCEPTED = "CONNECTION_ACCEPTED"
    STAFF_JOINED = "STAFF_JOINED"
    FEEDBACK_PROMPT = "FEEDBACK_PROMPT"
    TYPE_CHOICES = [
        (NEW_MESSAGE, "New Message"),
        (CONNECTION_REQUEST, "Connection Request"),
        (CONNECTION_ACCEPTED, "Connection Accepted"),
        (STAFF_JOINED, "Staff Joined"),
        (FEEDBACK_PROMPT, "Feedback Prompt"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    reference_id = models.UUIDField(null=True, blank=True)
    reference_type = models.CharField(max_length=50, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "is_read"]),
        ]

    def __str__(self):
        return f"{self.notification_type} for {self.user_id}"

    @property
    def human_message(self):
        """Human-readable notification message."""
        messages = {
            self.NEW_MESSAGE: "You have a new message.",
            self.CONNECTION_REQUEST: "You have a new connection request.",
            self.CONNECTION_ACCEPTED: "Your connection request was accepted.",
            self.STAFF_JOINED: "An Upstream Literacy team member joined your conversation.",
            self.FEEDBACK_PROMPT: "How is your connection going? Share your feedback.",
        }
        return messages.get(self.notification_type, "You have a notification.")


class StaffAction(models.Model):
    """Immutable audit log. Append-only — no update or delete."""

    MESSAGE_DELETED = "MESSAGE_DELETED"
    MEMBER_SUSPENDED = "MEMBER_SUSPENDED"
    CONVERSATION_JOINED = "CONVERSATION_JOINED"
    BROADCAST_SENT = "BROADCAST_SENT"
    MESSAGE_SENT_TO_MEMBER = "MESSAGE_SENT_TO_MEMBER"
    ACTION_CHOICES = [
        (MESSAGE_DELETED, "Message Deleted"),
        (MEMBER_SUSPENDED, "Member Suspended"),
        (CONVERSATION_JOINED, "Conversation Joined"),
        (BROADCAST_SENT, "Broadcast Sent"),
        (MESSAGE_SENT_TO_MEMBER, "Message Sent to Member"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="staff_actions",
    )
    action_type = models.CharField(max_length=50, choices=ACTION_CHOICES)
    target_id = models.UUIDField(null=True, blank=True)
    target_type = models.CharField(max_length=50, null=True, blank=True)
    note = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.action_type} by {self.staff_id} at {self.timestamp}"
