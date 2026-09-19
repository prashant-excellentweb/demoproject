from apps.chat.models import Conversation, Message, MessageDraft
from apps.users.models import User


class DraftRepository:
    """Per-user unsent draft text for a conversation."""

    @staticmethod
    def get(conversation: Conversation, user: User) -> MessageDraft | None:
        return (
            MessageDraft.objects.select_related("reply_to", "reply_to__sender")
            .filter(conversation=conversation, user=user)
            .first()
        )

    @staticmethod
    def save(
        conversation: Conversation,
        user: User,
        content: str,
        reply_to: Message | None = None,
    ) -> MessageDraft:
        draft, _ = MessageDraft.objects.update_or_create(
            conversation=conversation,
            user=user,
            defaults={"content": content, "reply_to": reply_to},
        )
        return draft

    @staticmethod
    def clear(conversation: Conversation, user: User) -> None:
        MessageDraft.objects.filter(conversation=conversation, user=user).delete()
