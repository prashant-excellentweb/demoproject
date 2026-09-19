from apps.chat.models import Conversation
from apps.chat.repositories.conversation_repository import MessageRepository
from apps.users.models import User

MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 100
DEFAULT_LIMIT = 30
MAX_LIMIT = 50


class MessageSearchService:
    """In-chat and global message search for a participant."""

    @staticmethod
    def normalize_query(raw: str | None) -> str:
        return (raw or "").strip()[:MAX_QUERY_LENGTH]

    @staticmethod
    def search(
        user: User,
        query: str,
        *,
        conversation: Conversation | None = None,
        before_id: int | None = None,
        limit: int = DEFAULT_LIMIT,
    ):
        query = MessageSearchService.normalize_query(query)
        if len(query) < MIN_QUERY_LENGTH:
            return []
        limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
        return MessageRepository.search_messages(
            user,
            query,
            conversation=conversation,
            before_id=before_id,
            limit=limit,
        )
