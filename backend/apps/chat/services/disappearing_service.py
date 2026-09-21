from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.chat.models import Conversation, Message
from apps.chat.repositories.conversation_repository import MessageRepository
from apps.users.models import User

DURATION_DELTAS = {
    Conversation.DisappearingDuration.OFF: None,
    Conversation.DisappearingDuration.H24: timedelta(hours=24),
    Conversation.DisappearingDuration.D7: timedelta(days=7),
    Conversation.DisappearingDuration.D90: timedelta(days=90),
}


class DisappearingMessagesService:
    """Per-chat disappearing messages (24h / 7d / 90d)."""

    VALID = set(Conversation.DisappearingDuration.values)

    @staticmethod
    def timedelta_for(duration: str) -> timedelta | None:
        return DURATION_DELTAS.get(duration)

    @staticmethod
    def compute_expires_at(conversation: Conversation, *, now=None):
        delta = DisappearingMessagesService.timedelta_for(conversation.disappearing_messages)
        if delta is None:
            return None
        return (now or timezone.now()) + delta

    @staticmethod
    def apply_to_message(message: Message, conversation: Conversation) -> Message:
        expires_at = DisappearingMessagesService.compute_expires_at(conversation)
        if expires_at is None:
            return message
        message.expires_at = expires_at
        message.save(update_fields=["expires_at", "updated_at"])
        return message

    @staticmethod
    @transaction.atomic
    def set_duration(conversation: Conversation, user: User, duration: str) -> Conversation:
        duration = (duration or Conversation.DisappearingDuration.OFF).strip()
        if duration not in DisappearingMessagesService.VALID:
            raise ValueError(
                "Invalid duration. Use off, 24h, 7d, or 90d."
            )
        if not conversation.participants.filter(id=user.id).exists():
            raise PermissionError("Access denied.")
        conversation.disappearing_messages = duration
        conversation.save(update_fields=["disappearing_messages", "updated_at"])
        return conversation

    @staticmethod
    def purge_expired(*, conversation: Conversation | None = None, limit: int = 200) -> int:
        """Soft-delete expired messages. Returns count purged."""
        from apps.chat.consumers import broadcast_message_deleted

        now = timezone.now()
        qs = Message.objects.filter(
            expires_at__isnull=False,
            expires_at__lte=now,
            is_deleted=False,
        )
        if conversation is not None:
            qs = qs.filter(conversation=conversation)
        expired = list(qs.select_related("sender", "conversation")[:limit])
        for message in expired:
            MessageRepository.soft_delete_message(message, message.sender)
            broadcast_message_deleted(message)
        return len(expired)
