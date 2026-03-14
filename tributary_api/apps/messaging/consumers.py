"""WebSocket consumer for real-time chat."""
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.messaging.models import (
    ConversationParticipant,
    Message,
    Notification,
)


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for a single conversation thread."""

    async def connect(self):
        self.conversation_id = str(
            self.scope["url_route"]["kwargs"]["conversation_id"]
        )
        self.user = self.scope["user"]

        # Reject anonymous users
        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        # Reject non-participants
        if not await self._is_participant():
            await self.close(code=4003)
            return

        self.group_name = f"chat_{self.conversation_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def receive(self, text_data):
        data = json.loads(text_data)
        body = data.get("body", "").strip()

        if not body or len(body) > 5000:
            await self.send(text_data=json.dumps({
                "type": "error",
                "code": "INVALID_MESSAGE",
                "message": "Message must be 1-5000 characters.",
            }))
            return

        msg = await self._save_message(
            body,
            data.get("attachment_url"),
            data.get("attachment_type"),
        )

        await self.channel_layer.group_send(self.group_name, {
            "type": "chat.message",
            "message_id": str(msg.id),
            "sender_id": str(self.user.id),
            "sender_name": await self._get_full_name(),
            "body": body,
            "sent_at": msg.sent_at.isoformat(),
            "attachment_url": msg.attachment_url,
            "attachment_type": msg.attachment_type,
        })

        await self._create_notifications(msg)

    async def chat_message(self, event):
        """Relay message to WebSocket client."""
        await self.send(text_data=json.dumps(event))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name, self.channel_name
            )

    # ---- DB helpers ----

    @database_sync_to_async
    def _is_participant(self):
        return ConversationParticipant.objects.filter(
            user=self.user,
            conversation_id=self.conversation_id,
        ).exists()

    @database_sync_to_async
    def _save_message(self, body, attachment_url, attachment_type):
        return Message.objects.create(
            conversation_id=self.conversation_id,
            sender=self.user,
            body=body,
            attachment_url=attachment_url or None,
            attachment_type=attachment_type or None,
        )

    @database_sync_to_async
    def _get_full_name(self):
        return self.user.get_full_name()

    @database_sync_to_async
    def _create_notifications(self, msg):
        participants = ConversationParticipant.objects.filter(
            conversation_id=self.conversation_id,
        ).exclude(user=self.user)

        notifications = [
            Notification(
                user_id=p.user_id,
                notification_type=Notification.NEW_MESSAGE,
                reference_id=msg.conversation_id,
                reference_type="Conversation",
            )
            for p in participants
        ]
        Notification.objects.bulk_create(notifications)
