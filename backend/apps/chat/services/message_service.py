import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.chat.models import Conversation, Message
from apps.chat.repositories.conversation_repository import (
    ConversationRepository,
    MessageRepository,
)
from apps.chat.repositories.draft_repository import DraftRepository
from apps.users.models import User

logger = logging.getLogger(__name__)


class MessageService:
    """Business rules for replying to, forwarding, and editing messages."""

    MAX_FORWARD_TARGETS = 10

    @staticmethod
    def edit_window_minutes() -> int:
        return int(getattr(settings, "MESSAGE_EDIT_WINDOW_MINUTES", 15))

    @staticmethod
    def is_within_edit_window(message: Message) -> bool:
        window = timedelta(minutes=MessageService.edit_window_minutes())
        return timezone.now() <= message.created_at + window

    @staticmethod
    def edit_message(message: Message, user: User, content: str, *, is_blocked: bool = False) -> Message:
        """
        Sender-only text edit inside MESSAGE_EDIT_WINDOW_MINUTES.

        Raises PermissionError for authz failures and ValueError for validation.
        """
        if is_blocked:
            raise PermissionError("You blocked this chat. Unblock to edit messages.")
        if message.sender_id != user.id:
            raise PermissionError("Only the sender can edit this message.")
        if message.is_deleted:
            raise ValueError("Cannot edit a deleted message.")
        if message.message_type != Message.MessageType.TEXT:
            raise ValueError("Only text messages can be edited.")
        if not MessageService.is_within_edit_window(message):
            raise ValueError(
                f"Edit window expired. Messages can be edited for "
                f"{MessageService.edit_window_minutes()} minutes after sending."
            )

        content = (content or "").strip()
        if not content:
            raise ValueError("Edited text cannot be empty.")
        if content == (message.content or "").strip():
            return message

        updated = MessageRepository.update_content(message, content)
        logger.info("User %s edited message %s", user.id, message.id)
        return updated

    @staticmethod
    def resolve_reply_target(conversation: Conversation, reply_to_id: int | None) -> Message | None:
        """
        Validate an inline-reply target.

        Raises ValueError when the quoted message is missing, deleted, or
        belongs to a different conversation.
        """
        if not reply_to_id:
            return None
        target = MessageRepository.get_quotable_message(conversation, reply_to_id)
        if target is None:
            raise ValueError("Replied message not found in this conversation.")
        return target

    @staticmethod
    @transaction.atomic
    def forward_message(
        message: Message,
        sender: User,
        conversation_ids: list[int],
    ) -> tuple[list[Message], list[dict]]:
        """
        Copy `message` into each target conversation.

        Returns `(created_messages, failures)`; failures carry a per-target reason
        so a partial forward still reports what went wrong.
        """
        targets = list(dict.fromkeys(conversation_ids))[: MessageService.MAX_FORWARD_TARGETS]

        # Single query for all targets, with participation resolved up front (no N+1).
        allowed = {
            conv.id: conv
            for conv in Conversation.objects.filter(id__in=targets, participants=sender)
        }
        blocked_ids = set(
            Conversation.objects.filter(id__in=targets, blocked_by__user=sender).values_list(
                "id", flat=True
            )
        )

        # A forward of a forward keeps pointing at the original message.
        origin = message.forwarded_from or message

        created: list[Message] = []
        failures: list[dict] = []

        for conversation_id in targets:
            conversation = allowed.get(conversation_id)
            if conversation is None:
                failures.append({"conversation_id": conversation_id, "error": "Access denied."})
                continue
            if conversation_id in blocked_ids:
                failures.append(
                    {"conversation_id": conversation_id, "error": "You blocked this chat."}
                )
                continue

            copy = MessageRepository.create_message(
                conversation=conversation,
                sender=sender,
                content=message.content,
                message_type=message.message_type,
                # Reuse the stored file instead of duplicating bytes on disk.
                file=message.file.name if message.file else None,
                file_name=message.file_name,
                file_size=message.file_size,
                forwarded_from=origin,
                is_forwarded=True,
            )
            created.append(copy)

        logger.info(
            "User %s forwarded message %s to %s chat(s), %s failed",
            sender.id,
            message.id,
            len(created),
            len(failures),
        )
        return created, failures

    @staticmethod
    def clear_draft_after_send(conversation: Conversation, user: User) -> None:
        """Sending a message discards the draft that produced it."""
        DraftRepository.clear(conversation, user)

    @staticmethod
    def can_access(conversation: Conversation, user: User) -> bool:
        return ConversationRepository.user_in_conversation(conversation, user)
