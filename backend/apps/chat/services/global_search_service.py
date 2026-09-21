from apps.chat.models import Conversation, Message
from apps.chat.repositories.conversation_repository import MessageRepository
from apps.chat.services.message_search_service import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    MIN_QUERY_LENGTH,
    MessageSearchService,
)
from apps.users.models import User

MEDIA_FILTER_TYPES = {
    "photos": [Message.MessageType.IMAGE],
    "videos": [Message.MessageType.VIDEO],
    "docs": [Message.MessageType.PDF, Message.MessageType.DOCUMENT],
    "audio": [Message.MessageType.AUDIO],
    "links": None,  # special: text with URL
}


class GlobalSearchService:
    """
    Unified inbox search: contacts, groups, messages, media, links, docs.

    Message-type buckets reuse the same hit shape as message search.
    """

    @staticmethod
    def search(user: User, query: str, *, limit: int = DEFAULT_LIMIT) -> dict:
        query = MessageSearchService.normalize_query(query)
        limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
        empty = {
            "query": query,
            "contacts": [],
            "groups": [],
            "messages": [],
            "media": [],
            "links": [],
            "docs": [],
        }
        if len(query) < MIN_QUERY_LENGTH:
            return empty

        contacts = GlobalSearchService._search_contacts(user, query, limit=limit)
        groups = GlobalSearchService._search_groups(user, query, limit=limit)
        messages = MessageRepository.search_messages(user, query, limit=limit)
        media = MessageRepository.search_messages(
            user,
            query,
            limit=limit,
            message_types=[Message.MessageType.IMAGE, Message.MessageType.VIDEO],
        )
        docs = MessageRepository.search_messages(
            user,
            query,
            limit=limit,
            message_types=[Message.MessageType.PDF, Message.MessageType.DOCUMENT],
        )
        links = MessageRepository.search_link_messages(user, query, limit=limit)

        return {
            "query": query,
            "contacts": contacts,
            "groups": groups,
            "messages": messages,
            "media": media,
            "links": links,
            "docs": docs,
        }

    @staticmethod
    def _search_contacts(user: User, query: str, *, limit: int) -> list[User]:
        """People you share a chat with, matching name or phone."""
        return list(
            User.objects.filter(conversations__participants=user)
            .exclude(id=user.id)
            .filter(
                Q(display_name__icontains=query) | Q(phone_number__icontains=query)
            )
            .distinct()
            .only(
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
            )[:limit]
        )

    @staticmethod
    def _search_groups(user: User, query: str, *, limit: int) -> list[Conversation]:
        return list(
            Conversation.objects.filter(participants=user, is_group=True, group_name__icontains=query)
            .prefetch_related("participants")
            .order_by("-updated_at")[:limit]
        )


class MediaFilterService:
    """In-chat media / links / docs gallery filters."""

    @staticmethod
    def list_media(
        conversation: Conversation,
        user: User,
        media_type: str,
        *,
        before_id: int | None = None,
        limit: int = 40,
    ):
        media_type = (media_type or "photos").lower().strip()
        if media_type not in MEDIA_FILTER_TYPES:
            raise ValueError(
                "Invalid type. Use photos, videos, links, docs, or audio."
            )
        limit = max(1, min(int(limit or 40), 50))
        return MessageRepository.list_media_messages(
            conversation,
            user,
            media_type=media_type,
            before_id=before_id,
            limit=limit,
        )
