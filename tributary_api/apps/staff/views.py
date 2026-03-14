"""Staff moderation API views."""
import redis
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.messaging.models import (
    Conversation,
    ConversationParticipant,
    Message,
    Notification,
    StaffAction,
)
from apps.messaging.serializers import ConversationListSerializer, MessageSerializer
from apps.staff.permissions import IsUpstreamStaff
from apps.staff.serializers import StaffBroadcastSerializer, StaffDirectMessageSerializer
from apps.users.utils import err, ok

_redis = redis.Redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)

BROADCAST_LIMIT = 3
BROADCAST_WINDOW = 86400  # 24 hours


class StaffConversationListView(APIView):
    """GET — all conversations with optional filters."""

    permission_classes = [IsUpstreamStaff]

    def get(self, request):
        qs = Conversation.objects.prefetch_related(
            "participants__user", "messages"
        ).order_by("-created_at")

        user_id = request.query_params.get("user_id")
        if user_id:
            convo_ids = ConversationParticipant.objects.filter(
                user_id=user_id
            ).values_list("conversation_id", flat=True)
            qs = qs.filter(id__in=convo_ids)

        staff_only = request.query_params.get("staff_initiated")
        if staff_only == "true":
            qs = qs.filter(is_staff_initiated=True)

        serializer = ConversationListSerializer(
            qs[:100], many=True, context={"request": request}
        )
        return ok(serializer.data)


class StaffConversationJoinView(APIView):
    """POST — staff joins a conversation."""

    permission_classes = [IsUpstreamStaff]

    def post(self, request, conversation_id):
        try:
            convo = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return err("NOT_FOUND", "Conversation not found.", status=404)

        _, created = ConversationParticipant.objects.get_or_create(
            conversation=convo, user=request.user
        )

        if created:
            Message.objects.create(
                conversation=convo,
                sender=request.user,
                body=f"{request.user.get_full_name()} (Upstream Literacy staff) joined the conversation.",
                system_message=True,
            )

            participants = convo.participants.exclude(user=request.user)
            Notification.objects.bulk_create([
                Notification(
                    user_id=p.user_id,
                    notification_type=Notification.STAFF_JOINED,
                    reference_id=convo.id,
                    reference_type="Conversation",
                )
                for p in participants
            ])

            StaffAction.objects.create(
                staff=request.user,
                action_type=StaffAction.CONVERSATION_JOINED,
                target_id=convo.id,
                target_type="Conversation",
            )

        return ok({"status": "joined"})


class StaffMessageDeleteView(APIView):
    """DELETE — soft-delete a message."""

    permission_classes = [IsUpstreamStaff]

    def delete(self, request, message_id):
        try:
            msg = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return err("NOT_FOUND", "Message not found.", status=404)

        if msg.is_deleted:
            return err("ALREADY_DELETED", "Message already deleted.")

        msg.is_deleted = True
        msg.deleted_by = request.user
        msg.save(update_fields=["is_deleted", "deleted_by"])

        StaffAction.objects.create(
            staff=request.user,
            action_type=StaffAction.MESSAGE_DELETED,
            target_id=msg.id,
            target_type="Message",
            note=request.data.get("note", ""),
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class StaffDirectMessageView(APIView):
    """POST — DM any member (creates staff-initiated conversation if needed)."""

    permission_classes = [IsUpstreamStaff]

    def post(self, request):
        serializer = StaffDirectMessageSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = list(serializer.errors.values())[0]
            msg = first_error[0] if isinstance(first_error, list) else str(first_error)
            return err("VALIDATION_ERROR", str(msg))

        recipient_id = serializer.validated_data["recipient_id"]
        body = serializer.validated_data["body"]

        from apps.users.models import User

        try:
            User.objects.get(id=recipient_id, is_active=True)
        except User.DoesNotExist:
            return err("NOT_FOUND", "User not found.", status=404)

        my_convos = ConversationParticipant.objects.filter(
            user=request.user
        ).values_list("conversation_id", flat=True)
        existing = ConversationParticipant.objects.filter(
            user_id=recipient_id,
            conversation_id__in=my_convos,
        ).select_related("conversation").first()

        if existing:
            convo = existing.conversation
        else:
            convo = Conversation.objects.create(is_staff_initiated=True)
            ConversationParticipant.objects.create(
                conversation=convo, user=request.user
            )
            ConversationParticipant.objects.create(
                conversation=convo, user_id=recipient_id
            )

        msg = Message.objects.create(
            conversation=convo, sender=request.user, body=body,
        )

        Notification.objects.create(
            user_id=recipient_id,
            notification_type=Notification.NEW_MESSAGE,
            reference_id=convo.id,
            reference_type="Conversation",
        )

        StaffAction.objects.create(
            staff=request.user,
            action_type=StaffAction.MESSAGE_SENT_TO_MEMBER,
            target_id=recipient_id,
            target_type="User",
        )

        return ok(MessageSerializer(msg).data)


class StaffBroadcastView(APIView):
    """POST — broadcast to multiple members. Rate-limited: 3/24h via Redis."""

    permission_classes = [IsUpstreamStaff]

    def post(self, request):
        serializer = StaffBroadcastSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = list(serializer.errors.values())[0]
            msg = first_error[0] if isinstance(first_error, list) else str(first_error)
            return err("VALIDATION_ERROR", str(msg))

        body = serializer.validated_data["body"]
        recipient_ids = serializer.validated_data["recipient_ids"]

        rate_key = f"broadcast:{request.user.id}"
        current = _redis.get(rate_key)
        if current and int(current) >= BROADCAST_LIMIT:
            return err(
                "RATE_LIMIT_EXCEEDED",
                "Broadcast limit reached (3 per 24 hours).",
                status=429,
            )

        from apps.users.models import User

        recipients = User.objects.filter(id__in=recipient_ids, is_active=True)
        if not recipients.exists():
            return err("NO_RECIPIENTS", "No valid recipients.")

        for recipient in recipients:
            convo = Conversation.objects.create(is_staff_initiated=True)
            ConversationParticipant.objects.create(
                conversation=convo, user=request.user
            )
            ConversationParticipant.objects.create(
                conversation=convo, user=recipient
            )
            Message.objects.create(
                conversation=convo, sender=request.user, body=body
            )
            Notification.objects.create(
                user_id=recipient.id,
                notification_type=Notification.NEW_MESSAGE,
                reference_id=convo.id,
                reference_type="Conversation",
            )

        pipe = _redis.pipeline()
        pipe.incr(rate_key)
        pipe.expire(rate_key, BROADCAST_WINDOW)
        pipe.execute()

        StaffAction.objects.create(
            staff=request.user,
            action_type=StaffAction.BROADCAST_SENT,
            note=f"Broadcast to {recipients.count()} recipients.",
        )

        return ok({"status": "broadcast_sent", "recipient_count": recipients.count()})


class StaffSuspendUserView(APIView):
    """POST — suspend a member (set is_active=False)."""

    permission_classes = [IsUpstreamStaff]

    def post(self, request, user_id):
        from apps.users.models import User

        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return err("NOT_FOUND", "User not found.", status=404)

        if target.role in ("UPSTREAM_STAFF", "PLATFORM_ADMIN"):
            return err("FORBIDDEN", "Cannot suspend staff or admin users.", status=403)

        if not target.is_active:
            return err("ALREADY_SUSPENDED", "User is already suspended.")

        target.is_active = False
        target.save(update_fields=["is_active"])

        StaffAction.objects.create(
            staff=request.user,
            action_type=StaffAction.MEMBER_SUSPENDED,
            target_id=target.id,
            target_type="User",
            note=request.data.get("note", ""),
        )

        return ok({"status": "suspended"})
