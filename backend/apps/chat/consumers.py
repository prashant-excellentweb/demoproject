import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken

from apps.chat.models import Conversation, Message
from apps.chat.repositories.conversation_repository import ConversationRepository, MessageRepository
from apps.chat.serializers import MessageSerializer
from apps.users.models import User


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = await self.get_user_from_token()
        if not self.user or isinstance(self.user, AnonymousUser):
            await self.close()
            return

        self.user_group = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.set_online(True)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)
        if hasattr(self, "conversation_group"):
            await self.channel_layer.group_discard(self.conversation_group, self.channel_name)
        if hasattr(self, "user") and self.user and not isinstance(self.user, AnonymousUser):
            await self.set_online(False)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")

        if action == "join_conversation":
            await self.join_conversation(data.get("conversation_id"))
        elif action == "leave_conversation":
            await self.leave_conversation()
        elif action == "typing":
            await self.broadcast_typing(data)
        elif action == "mark_read":
            await self.mark_read(data.get("conversation_id"))

    async def join_conversation(self, conversation_id):
        if not conversation_id:
            return
        allowed = await self.user_in_conversation(conversation_id)
        if not allowed:
            return
        if hasattr(self, "conversation_group"):
            await self.channel_layer.group_discard(self.conversation_group, self.channel_name)
        self.conversation_group = f"conversation_{conversation_id}"
        await self.channel_layer.group_add(self.conversation_group, self.channel_name)

    async def leave_conversation(self):
        if hasattr(self, "conversation_group"):
            await self.channel_layer.group_discard(self.conversation_group, self.channel_name)
            del self.conversation_group

    async def broadcast_typing(self, data):
        if not hasattr(self, "conversation_group"):
            return
        await self.channel_layer.group_send(
            self.conversation_group,
            {
                "type": "typing_indicator",
                "user_id": self.user.id,
                "user_name": self.user.display_name or self.user.phone_number,
                "is_typing": data.get("is_typing", False),
            },
        )

    async def mark_read(self, conversation_id):
        if conversation_id:
            await self.mark_messages_read(conversation_id)

    async def typing_indicator(self, event):
        if event["user_id"] != self.user.id:
            await self.send(text_data=json.dumps({"type": "typing", **event}))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({"type": "message", "message": event["message"]}))

    async def message_read(self, event):
        await self.send(text_data=json.dumps({"type": "read", **event}))

    @database_sync_to_async
    def get_user_from_token(self):
        from urllib.parse import parse_qs

        query_string = self.scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token_list = params.get("token", [])
        token = token_list[0] if token_list else None
        if not token:
            return None
        try:
            access = AccessToken(token)
            return User.objects.get(id=access["user_id"])
        except Exception:
            return None

    @database_sync_to_async
    def user_in_conversation(self, conversation_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
            return ConversationRepository.user_in_conversation(conv, self.user)
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def mark_messages_read(self, conversation_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
            if ConversationRepository.user_in_conversation(conv, self.user):
                MessageRepository.mark_as_read(conv, self.user)
        except Conversation.DoesNotExist:
            pass

    @database_sync_to_async
    def set_online(self, online: bool):
        from django.utils import timezone
        self.user.is_online = online
        self.user.last_seen = timezone.now()
        self.user.save(update_fields=["is_online", "last_seen"])


def broadcast_new_message(message: Message, request=None):
    """Broadcast a new message to conversation participants via channel layer."""
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    serialized = MessageSerializer(message, context={"request": request}).data

    async_to_sync(channel_layer.group_send)(
        f"conversation_{message.conversation_id}",
        {"type": "chat_message", "message": serialized},
    )

    for participant in message.conversation.participants.all():
        async_to_sync(channel_layer.group_send)(
            f"user_{participant.id}",
            {"type": "chat_message", "message": serialized},
        )
