import os

from django.db import transaction
from django.db.models import Case, Count, Exists, IntegerField, Max, OuterRef, Prefetch, Q, Value, When
from django.utils import timezone

from apps.chat.models import (
    Conversation,
    ConversationFavourite,
    Message,
    MessageHidden,
    MessageReaction,
    MessageStatus,
)
from apps.users.models import User


class ConversationRepository:
    FILTER_ALL = "all"
    FILTER_UNREAD = "unread"
    FILTER_GROUPS = "groups"
    FILTER_FAVOURITES = "favourites"
    VALID_FILTERS = {FILTER_ALL, FILTER_UNREAD, FILTER_GROUPS, FILTER_FAVOURITES}

    @staticmethod
    def get_user_conversations(user: User, filter_by: str = "all"):
        filter_by = (filter_by or "all").lower().strip()
        if filter_by not in ConversationRepository.VALID_FILTERS:
            filter_by = ConversationRepository.FILTER_ALL

        favourite_exists = ConversationFavourite.objects.filter(
            conversation_id=OuterRef("pk"),
            user=user,
        )

        qs = (
            Conversation.objects.filter(participants=user)
            .select_related("created_by")
            .prefetch_related(
                Prefetch(
                    "participants",
                    queryset=User.objects.only(
                        "id", "display_name", "phone_number", "avatar", "is_online", "last_seen", "about"
                    ),
                ),
                Prefetch(
                    "messages",
                    queryset=Message.objects.select_related("sender")
                    .prefetch_related("reactions__user")
                    .exclude(hidden_for__user=user)
                    .order_by("-created_at")[:1],
                    to_attr="latest_messages",
                ),
            )
            .annotate(
                unread_count=Count(
                    "messages",
                    filter=Q(messages__is_read=False)
                    & Q(messages__is_deleted=False)
                    & ~Q(messages__sender=user)
                    & ~Q(messages__hidden_for__user=user),
                    distinct=True,
                ),
                last_message_time=Max("messages__created_at"),
                is_favourite=Exists(favourite_exists),
            )
        )

        if filter_by == ConversationRepository.FILTER_UNREAD:
            qs = qs.filter(unread_count__gt=0)
        elif filter_by == ConversationRepository.FILTER_GROUPS:
            qs = qs.filter(is_group=True)
        elif filter_by == ConversationRepository.FILTER_FAVOURITES:
            qs = qs.filter(is_favourite=True)

        return qs.order_by(
            Case(When(is_favourite=True, then=Value(0)), default=Value(1), output_field=IntegerField()),
            "-updated_at",
        )

    @staticmethod
    def toggle_favourite(conversation: Conversation, user: User) -> bool:
        """Returns True if now favourited, False if removed."""
        fav, created = ConversationFavourite.objects.get_or_create(
            conversation=conversation,
            user=user,
        )
        if not created:
            fav.delete()
            return False
        return True

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

    @staticmethod
    def remove_participant(conversation: Conversation, user: User) -> None:
        conversation.participants.remove(user)


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
    def get_conversation_messages(
        conversation: Conversation,
        user: User,
        limit: int = 50,
        before_id: int | None = None,
    ):
        qs = (
            Message.objects.filter(conversation=conversation)
            .exclude(hidden_for__user=user)
            .select_related("sender")
            .prefetch_related("reactions__user")
        )
        if before_id:
            qs = qs.filter(id__lt=before_id)
        return qs.order_by("-created_at")[:limit]

    @staticmethod
    def mark_as_read(conversation: Conversation, user: User):
        Message.objects.filter(
            conversation=conversation,
            is_read=False,
            is_deleted=False,
        ).exclude(sender=user).exclude(hidden_for__user=user).update(is_read=True)
        MessageStatus.objects.filter(
            message__conversation=conversation,
            user=user,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())

    @staticmethod
    def soft_delete_message(message: Message, deleted_by: User) -> Message:
        """Delete for everyone — clear content/media and mark as deleted."""
        if message.file:
            message.file.delete(save=False)
        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.deleted_by = deleted_by
        message.content = ""
        message.file = None
        message.file_name = ""
        message.file_size = 0
        message.save(
            update_fields=[
                "is_deleted",
                "deleted_at",
                "deleted_by",
                "content",
                "file",
                "file_name",
                "file_size",
                "updated_at",
            ]
        )
        message.reactions.all().delete()
        return message

    @staticmethod
    def hide_message_for_user(message: Message, user: User) -> None:
        """Delete for me — hide only for this user."""
        MessageHidden.objects.get_or_create(message=message, user=user)

    @staticmethod
    def toggle_reaction(message: Message, user: User, emoji: str) -> Message:
        """Add, change, or remove a user's reaction. One reaction per user."""
        emoji = (emoji or "").strip()
        existing = MessageReaction.objects.filter(message=message, user=user).first()
        if existing:
            if existing.emoji == emoji:
                existing.delete()
            else:
                existing.emoji = emoji
                existing.save(update_fields=["emoji"])
        else:
            MessageReaction.objects.create(message=message, user=user, emoji=emoji)
        return (
            Message.objects.select_related("sender")
            .prefetch_related("reactions__user")
            .get(id=message.id)
        )
