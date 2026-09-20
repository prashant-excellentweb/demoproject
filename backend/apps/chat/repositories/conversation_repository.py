import os

from django.db import transaction
from django.db.models import Case, Count, Exists, IntegerField, Max, OuterRef, Prefetch, Q, Value, When
from django.utils import timezone

from apps.chat.models import (
    Conversation,
    ConversationArchive,
    ConversationBlock,
    ConversationFavourite,
    ConversationPin,
    Message,
    MessageDraft,
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
    FILTER_ARCHIVED = "archived"
    FILTER_BLOCKED = "blocked"
    VALID_FILTERS = {
        FILTER_ALL,
        FILTER_UNREAD,
        FILTER_GROUPS,
        FILTER_FAVOURITES,
        FILTER_ARCHIVED,
        FILTER_BLOCKED,
    }

    @staticmethod
    def get_user_conversations(user: User, filter_by: str = "all"):
        filter_by = (filter_by or "all").lower().strip()
        if filter_by not in ConversationRepository.VALID_FILTERS:
            filter_by = ConversationRepository.FILTER_ALL

        favourite_exists = ConversationFavourite.objects.filter(
            conversation_id=OuterRef("pk"),
            user=user,
        )
        archived_exists = ConversationArchive.objects.filter(
            conversation_id=OuterRef("pk"),
            user=user,
        )
        blocked_exists = ConversationBlock.objects.filter(
            conversation_id=OuterRef("pk"),
            user=user,
        )
        pinned_exists = ConversationPin.objects.filter(
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
                        "id",
                        "display_name",
                        "phone_number",
                        "avatar",
                        "is_online",
                        "last_seen",
                        "about",
                        "profile_photo_privacy",
                        "about_privacy",
                        "last_seen_privacy",
                        "status_privacy",
                    ),
                ),
                Prefetch(
                    "messages",
                    queryset=Message.objects.select_related(
                        "sender", "reply_to", "reply_to__sender"
                    )
                    .prefetch_related("reactions__user", "mention_links__user")
                    .exclude(hidden_for__user=user)
                    .order_by("-created_at")[:1],
                    to_attr="latest_messages",
                ),
                Prefetch(
                    "drafts",
                    queryset=MessageDraft.objects.filter(user=user).select_related(
                        "reply_to", "reply_to__sender"
                    ),
                    to_attr="user_drafts",
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
                is_archived=Exists(archived_exists),
                is_blocked=Exists(blocked_exists),
                is_pinned=Exists(pinned_exists),
            )
        )

        if filter_by == ConversationRepository.FILTER_ARCHIVED:
            qs = qs.filter(is_archived=True)
        elif filter_by == ConversationRepository.FILTER_BLOCKED:
            qs = qs.filter(is_blocked=True)
        else:
            # Main inbox filters hide archived chats
            qs = qs.filter(is_archived=False)
            if filter_by == ConversationRepository.FILTER_UNREAD:
                qs = qs.filter(unread_count__gt=0)
            elif filter_by == ConversationRepository.FILTER_GROUPS:
                qs = qs.filter(is_group=True)
            elif filter_by == ConversationRepository.FILTER_FAVOURITES:
                qs = qs.filter(is_favourite=True)

        return qs.order_by(
            Case(When(is_pinned=True, then=Value(0)), default=Value(1), output_field=IntegerField()),
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
    def set_archived(conversation: Conversation, user: User, archived: bool) -> bool:
        if archived:
            ConversationArchive.objects.get_or_create(conversation=conversation, user=user)
            return True
        ConversationArchive.objects.filter(conversation=conversation, user=user).delete()
        return False

    @staticmethod
    def set_blocked(conversation: Conversation, user: User, blocked: bool) -> bool:
        if blocked:
            ConversationBlock.objects.get_or_create(conversation=conversation, user=user)
            return True
        ConversationBlock.objects.filter(conversation=conversation, user=user).delete()
        return False

    @staticmethod
    def set_pinned(conversation: Conversation, user: User, pinned: bool) -> bool:
        if pinned:
            ConversationPin.objects.get_or_create(conversation=conversation, user=user)
            return True
        ConversationPin.objects.filter(conversation=conversation, user=user).delete()
        return False

    @staticmethod
    def is_blocked_by(conversation: Conversation, user: User) -> bool:
        return ConversationBlock.objects.filter(conversation=conversation, user=user).exists()

    @staticmethod
    def unarchive_for_participants(conversation: Conversation) -> None:
        """Incoming/outgoing activity restores chat to main list for everyone."""
        ConversationArchive.objects.filter(conversation=conversation).delete()

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
        reply_to: Message | None = None,
        forwarded_from: Message | None = None,
        is_forwarded: bool = False,
        file_size: int | None = None,
    ) -> Message:
        if file_size is None:
            file_size = file.size if file else 0
        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            message_type=message_type,
            content=content,
            file=file,
            file_name=file_name or (file.name if file else ""),
            file_size=file_size,
            reply_to=reply_to,
            forwarded_from=forwarded_from,
            is_forwarded=is_forwarded,
        )
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=["updated_at"])

        MessageStatus.objects.bulk_create(
            [
                MessageStatus(message=message, user=participant)
                for participant in conversation.participants.exclude(id=sender.id)
            ]
        )

        # New activity brings archived chats back into the main inbox
        ConversationRepository.unarchive_for_participants(conversation)
        return message

    @staticmethod
    def get_quotable_message(conversation: Conversation, message_id: int) -> Message | None:
        """Message that can be quoted/forwarded from this conversation, or None."""
        return (
            Message.objects.filter(
                id=message_id,
                conversation=conversation,
                is_deleted=False,
            )
            .select_related("sender")
            .first()
        )

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
            .select_related("sender", "reply_to", "reply_to__sender")
            .prefetch_related("reactions__user", "mention_links__user")
        )
        if before_id:
            qs = qs.filter(id__lt=before_id)
        return qs.order_by("-created_at")[:limit]

    @staticmethod
    def get_messages_around(
        conversation: Conversation,
        user: User,
        around_id: int,
        limit: int = 50,
    ):
        """Chronological window of messages centered on `around_id` (for search jump)."""
        visible = (
            Message.objects.filter(conversation=conversation)
            .exclude(hidden_for__user=user)
        )
        try:
            target = (
                visible.select_related("sender", "reply_to", "reply_to__sender")
                .prefetch_related("reactions__user", "mention_links__user")
                .get(id=around_id)
            )
        except Message.DoesNotExist:
            return []

        half = max(limit // 2, 1)
        older = list(
            visible.filter(
                Q(created_at__lt=target.created_at)
                | Q(created_at=target.created_at, id__lt=target.id)
            )
            .select_related("sender", "reply_to", "reply_to__sender")
            .prefetch_related("reactions__user", "mention_links__user")
            .order_by("-created_at", "-id")[:half]
        )
        newer = list(
            visible.filter(
                Q(created_at__gt=target.created_at)
                | Q(created_at=target.created_at, id__gt=target.id)
            )
            .select_related("sender", "reply_to", "reply_to__sender")
            .prefetch_related("reactions__user", "mention_links__user")
            .order_by("created_at", "id")[:half]
        )
        return list(reversed(older)) + [target] + newer

    @staticmethod
    def search_messages(
        user: User,
        query: str,
        *,
        conversation: Conversation | None = None,
        before_id: int | None = None,
        limit: int = 30,
    ):
        """
        Text/file-name search over messages the user can see.

        Newest first. `before_id` is a cursor (created_at, id) of the last hit.
        """
        qs = Message.objects.filter(
            conversation__participants=user,
            is_deleted=False,
        ).exclude(hidden_for__user=user)
        if conversation is not None:
            qs = qs.filter(conversation=conversation)
        qs = qs.filter(Q(content__icontains=query) | Q(file_name__icontains=query))
        if before_id:
            cursor = (
                Message.objects.filter(id=before_id)
                .values("created_at", "id")
                .first()
            )
            if cursor:
                qs = qs.filter(
                    Q(created_at__lt=cursor["created_at"])
                    | Q(created_at=cursor["created_at"], id__lt=cursor["id"])
                )
        return list(
            qs.select_related("sender", "conversation")
            .prefetch_related(
                Prefetch(
                    "conversation__participants",
                    queryset=User.objects.only(
                        "id",
                        "display_name",
                        "phone_number",
                        "avatar",
                        "is_online",
                        "last_seen",
                        "about",
                        "profile_photo_privacy",
                        "about_privacy",
                        "last_seen_privacy",
                        "status_privacy",
                    ),
                )
            )
            .order_by("-created_at", "-id")[:limit]
        )

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
            Message.objects.select_related("sender", "reply_to", "reply_to__sender")
            .prefetch_related("reactions__user", "mention_links__user")
            .get(id=message.id)
        )

    @staticmethod
    def update_content(message: Message, content: str) -> Message:
        """Persist an in-window content edit and return a serializer-ready row."""
        message.content = content
        message.edited_at = timezone.now()
        message.save(update_fields=["content", "edited_at", "updated_at"])
        return (
            Message.objects.select_related("sender", "reply_to", "reply_to__sender")
            .prefetch_related("reactions__user", "mention_links__user")
            .get(id=message.id)
        )
