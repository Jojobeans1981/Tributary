"""API views for messaging, notifications, and file upload."""
import uuid

import boto3
from botocore.config import Config as BotoConfig
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView

from apps.messaging.models import (
    Conversation,
    ConversationParticipant,
    Message,
    Notification,
)
from apps.messaging.serializers import (
    ConversationListSerializer,
    CreateConversationSerializer,
    CreateMessageSerializer,
    FileUploadSerializer,
    MessageSerializer,
    NotificationSerializer,
)
from apps.users.utils import err, ok


class ConversationListCreateView(APIView):
    """
    GET  — list my conversations with preview + unread count.
    POST — create a new conversation with another user.
    """

    def get(self, request):
        participant_ids = ConversationParticipant.objects.filter(
            user=request.user
        ).values_list("conversation_id", flat=True)

        conversations = (
            Conversation.objects.filter(id__in=participant_ids)
            .prefetch_related("participants__user", "messages")
            .order_by("-created_at")
        )

        serializer = ConversationListSerializer(
            conversations, many=True, context={"request": request}
        )
        return ok(serializer.data)

    def post(self, request):
        serializer = CreateConversationSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            first_error = list(serializer.errors.values())[0]
            msg = first_error[0] if isinstance(first_error, list) else str(first_error)
            return err("VALIDATION_ERROR", str(msg))

        participant_id = serializer.validated_data["participant_id"]

        # Check if a conversation already exists between these two users
        my_convos = ConversationParticipant.objects.filter(
            user=request.user
        ).values_list("conversation_id", flat=True)
        existing = ConversationParticipant.objects.filter(
            user_id=participant_id,
            conversation_id__in=my_convos,
        ).first()

        if existing:
            convo = existing.conversation
        else:
            is_staff = request.user.role in ("UPSTREAM_STAFF", "PLATFORM_ADMIN")
            convo = Conversation.objects.create(
                is_staff_initiated=is_staff,
            )
            ConversationParticipant.objects.create(
                conversation=convo, user=request.user
            )
            ConversationParticipant.objects.create(
                conversation=convo, user_id=participant_id
            )

        data = ConversationListSerializer(
            convo, context={"request": request}
        ).data
        return ok(data)


class ConversationMessagesView(APIView):
    """
    GET  — cursor-paginated messages (before={datetime}, 50/page).
    POST — send a message in this conversation.
    """

    def get(self, request, conversation_id):
        if not self._is_participant(request.user, conversation_id):
            return err("FORBIDDEN", "Not a participant.", status=403)

        qs = Message.objects.filter(
            conversation_id=conversation_id
        ).select_related("sender").order_by("-sent_at")

        before = request.query_params.get("before")
        if before:
            qs = qs.filter(sent_at__lt=before)

        messages = qs[:50]
        serializer = MessageSerializer(messages, many=True)
        return ok(serializer.data)

    def post(self, request, conversation_id):
        if not self._is_participant(request.user, conversation_id):
            return err("FORBIDDEN", "Not a participant.", status=403)

        serializer = CreateMessageSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = list(serializer.errors.values())[0]
            msg = first_error[0] if isinstance(first_error, list) else str(first_error)
            return err("VALIDATION_ERROR", str(msg))

        msg = Message.objects.create(
            conversation_id=conversation_id,
            sender=request.user,
            body=serializer.validated_data["body"],
            attachment_url=serializer.validated_data.get("attachment_url"),
            attachment_type=serializer.validated_data.get("attachment_type"),
        )

        # Create notifications for other participants
        participants = ConversationParticipant.objects.filter(
            conversation_id=conversation_id
        ).exclude(user=request.user)

        notifications = [
            Notification(
                user_id=p.user_id,
                notification_type=Notification.NEW_MESSAGE,
                reference_id=conversation_id,
                reference_type="Conversation",
            )
            for p in participants
        ]
        Notification.objects.bulk_create(notifications)

        # Trigger email notification task (skip if Celery/Redis unavailable)
        try:
            from apps.messaging.tasks import check_and_send_message_email

            for p in participants:
                check_and_send_message_email.delay(
                    str(p.user_id),
                    str(msg.id),
                )
        except Exception:
            pass

        # Schedule feedback prompt 7 days after the first message in a conversation
        msg_count = Message.objects.filter(conversation_id=conversation_id).count()
        if msg_count == 1:
            try:
                from django.db.models import Q

                from apps.matching.models import Connection
                from apps.matching.tasks import send_feedback_prompt

                participant_ids = list(
                    ConversationParticipant.objects.filter(
                        conversation_id=conversation_id
                    ).values_list("user_id", flat=True)
                )
                if len(participant_ids) == 2:
                    connection = Connection.objects.filter(
                        Q(
                            requester_id=participant_ids[0],
                            recipient_id=participant_ids[1],
                        )
                        | Q(
                            requester_id=participant_ids[1],
                            recipient_id=participant_ids[0],
                        ),
                        status=Connection.ACCEPTED,
                    ).first()
                    if connection:
                        send_feedback_prompt.apply_async(
                            args=[str(connection.id)],
                            countdown=604800,  # 7 days
                        )
            except Exception:
                pass

        data = MessageSerializer(msg).data
        return ok(data)

    @staticmethod
    def _is_participant(user, conversation_id):
        return ConversationParticipant.objects.filter(
            user=user, conversation_id=conversation_id
        ).exists()


class ConversationReadView(APIView):
    """PATCH — mark conversation as read (update last_read_at)."""

    def patch(self, request, conversation_id):
        updated = ConversationParticipant.objects.filter(
            user=request.user,
            conversation_id=conversation_id,
        ).update(last_read_at=timezone.now())

        if not updated:
            return err("NOT_FOUND", "Conversation not found.", status=404)
        return ok({"status": "ok"})


class FileUploadView(APIView):
    """POST — upload a file to S3, return presigned download URL (1hr TTL)."""

    def post(self, request):
        serializer = FileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            first_error = list(serializer.errors.values())[0]
            msg = first_error[0] if isinstance(first_error, list) else str(first_error)
            return err("VALIDATION_ERROR", str(msg))

        uploaded = serializer.validated_data["file"]
        ext = uploaded.name.rsplit(".", 1)[-1] if "." in uploaded.name else "bin"
        key = f"attachments/{uuid.uuid4()}.{ext}"

        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
            config=BotoConfig(signature_version="s3v4"),
        )

        s3.upload_fileobj(
            uploaded.file,
            settings.AWS_STORAGE_BUCKET_NAME,
            key,
            ExtraArgs={"ContentType": uploaded.content_type},
        )

        presigned_url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": key,
            },
            ExpiresIn=3600,
        )

        attachment_type = FileUploadSerializer.ALLOWED_TYPES[uploaded.content_type]
        return ok({
            "url": presigned_url,
            "attachment_type": attachment_type,
            "key": key,
        })


class NotificationListView(APIView):
    """GET — my notifications, 20/page, includes human_message."""

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)[:20]
        serializer = NotificationSerializer(notifications, many=True)
        return ok(serializer.data)


class NotificationReadAllView(APIView):
    """PATCH — mark all my notifications as read."""

    def patch(self, request):
        Notification.objects.filter(
            user=request.user, is_read=False
        ).update(is_read=True)
        return ok({"status": "ok"})
