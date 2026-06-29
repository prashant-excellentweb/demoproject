import os

from django.db import transaction
from django.db.models import Count, Max, Prefetch, Q
from django.utils import timezone

from apps.chat.models import Conversation, Message, MessageStatus
from apps.users.models import User


class ConversationRepository:
    @staticmethod
    def get_user_conversations(user: User):
        return (
            Conversation.objects.filter(participants=user)
            .prefetch_related(
                Prefetch("participants", queryset=User.objects.only(
                    "id", "display_name", "phone_number", "avatar", "is_online", "last_seen", "about"
                )),
                Prefetch(
                    "messages",
                    queryset=Message.objects.select_related("sender").order_by("-created_at")[:1],
                    to_attr="latest_messages",
                ),
            )
            .annotate(
                unread_count=Count(
                    "messages",
                    filter=Q(messages__is_read=False) & ~Q(messages__sender=user),
                ),
                last_message_time=Max("messages__created_at"),
            )
            .order_by("-updated_at")
        )

    @staticmethod
    def get_or_create_direct(user1: User, user2: User) -> Conversation:
        existing = (
            Conversation.objects.filter(is_group=False, participants=user1)
            .filter(participants=user2)
            .first()
        )
        if existing:
            return existing
        with transaction.atomic():
            conv = Conversation.objects.create(is_group=False)
            conv.participants.add(user1, user2)
        return conv

    @staticmethod
    def user_in_conversation(conversation: Conversation, user: User) -> bool:
        return conversation.participants.filter(id=user.id).exists()


class MessageRepository:
    ALLOWED_EXTENSIONS = {
        "image": {".jpg", ".jpeg", ".png", ".gif", ".webp"},
        "video": {".mp4", ".webm", ".mov", ".avi"},
        "pdf": {".pdf"},
        "document": {".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx"},
        "audio": {".mp3", ".wav", ".ogg", ".m4a"},
    }

    @staticmethod
    def detect_message_type(filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        for msg_type, extensions in MessageRepository.ALLOWED_EXTENSIONS.items():
            if ext in extensions:
                return msg_type
        return Message.MessageType.DOCUMENT

    @staticmethod
    def create_message(
        conversation: Conversation,
        sender: User,
        content: str = "",
        message_type: str = Message.MessageType.TEXT,
        file=None,
        file_name: str = "",
    ) -> Message:
        file_size = file.size if file else 0
        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            message_type=message_type,
            content=content,
            file=file,
            file_name=file_name or (file.name if file else ""),
            file_size=file_size,
        )
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=["updated_at"])

        for participant in conversation.participants.exclude(id=sender.id):
            MessageStatus.objects.create(message=message, user=participant)

        return message

    @staticmethod
    def get_conversation_messages(conversation: Conversation, limit: int = 50, before_id: int | None = None):
        qs = Message.objects.filter(conversation=conversation).select_related("sender")
        if before_id:
            qs = qs.filter(id__lt=before_id)
        return qs.order_by("-created_at")[:limit]

    @staticmethod
    def mark_as_read(conversation: Conversation, user: User):
        Message.objects.filter(
            conversation=conversation,
            is_read=False,
        ).exclude(sender=user).update(is_read=True)
        MessageStatus.objects.filter(
            message__conversation=conversation,
            user=user,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())
