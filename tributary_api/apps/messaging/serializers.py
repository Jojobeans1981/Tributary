"""Serializers for messaging, notifications, and file upload."""
from django.db.models import Q
from rest_framework import serializers

from apps.matching.models import Connection
from apps.messaging.models import (
    Conversation,
    ConversationParticipant,
    Message,
    Notification,
)


class ParticipantSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(source="user.id")
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return obj.user.get_full_name()


class ConversationListSerializer(serializers.ModelSerializer):
    last_message_preview = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "conversation_type",
            "is_staff_initiated",
            "created_at",
            "last_message_preview",
            "unread_count",
            "participants",
        ]

    def get_last_message_preview(self, obj):
        msg = (
            obj.messages.filter(is_deleted=False)
            .order_by("-sent_at")
            .values_list("body", flat=True)
            .first()
        )
        if msg:
            return msg[:60]
        return None

    def get_unread_count(self, obj):
        user = self.context["request"].user
        try:
            participant = obj.participants.get(user=user)
        except ConversationParticipant.DoesNotExist:
            return 0
        qs = obj.messages.filter(is_deleted=False).exclude(sender=user)
        if participant.last_read_at:
            qs = qs.filter(sent_at__gt=participant.last_read_at)
        return qs.count()

    def get_participants(self, obj):
        return ParticipantSerializer(
            obj.participants.all(), many=True
        ).data


class CreateConversationSerializer(serializers.Serializer):
    participant_id = serializers.UUIDField()

    def validate_participant_id(self, value):
        from apps.users.models import User

        user = self.context["request"].user
        if str(value) == str(user.id):
            raise serializers.ValidationError("Cannot start a conversation with yourself.")

        try:
            target = User.objects.get(id=value, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")

        # Staff can message anyone
        if user.role in ("UPSTREAM_STAFF", "PLATFORM_ADMIN"):
            return value

        # Check for BLOCKED connection in either direction
        blocked = Connection.objects.filter(
            Q(requester=user, recipient=target, status=Connection.BLOCKED)
            | Q(requester=target, recipient=user, status=Connection.BLOCKED)
        ).exists()
        if blocked:
            raise serializers.ValidationError("Cannot message a blocked user.")

        # Require ACCEPTED connection
        accepted = Connection.objects.filter(
            Q(requester=user, recipient=target, status=Connection.ACCEPTED)
            | Q(requester=target, recipient=user, status=Connection.ACCEPTED)
        ).exists()
        if not accepted:
            raise serializers.ValidationError(
                "You must have an accepted connection to start a conversation."
            )

        return value


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation_id",
            "sender_id",
            "sender_name",
            "body",
            "attachment_url",
            "attachment_type",
            "sent_at",
            "is_deleted",
            "system_message",
        ]

    def get_sender_name(self, obj):
        return obj.sender.get_full_name()

    def get_body(self, obj):
        if obj.is_deleted:
            return "[This message was removed by a moderator]"
        return obj.body


class CreateMessageSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=5000)
    attachment_url = serializers.URLField(required=False, allow_null=True)
    attachment_type = serializers.CharField(max_length=10, required=False, allow_null=True)


class NotificationSerializer(serializers.ModelSerializer):
    human_message = serializers.CharField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "reference_id",
            "reference_type",
            "is_read",
            "created_at",
            "human_message",
        ]


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    ALLOWED_TYPES = {
        "application/pdf": "PDF",
        "image/jpeg": "JPEG",
        "image/png": "PNG",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
    }
    MAX_SIZE = 10 * 1024 * 1024  # 10 MB

    def validate_file(self, value):
        if value.size > self.MAX_SIZE:
            raise serializers.ValidationError("File size must not exceed 10 MB.")
        if value.content_type not in self.ALLOWED_TYPES:
            raise serializers.ValidationError(
                f"Unsupported file type. Allowed: {', '.join(self.ALLOWED_TYPES.values())}"
            )
        return value
