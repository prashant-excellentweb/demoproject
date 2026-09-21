from django.utils import timezone

from apps.chat.models import Conversation, Message
from apps.users.models import User

VIEW_ONCE_TYPES = {Message.MessageType.IMAGE, Message.MessageType.VIDEO}


class ViewOnceService:
    """WhatsApp-style view-once photos/videos."""

    @staticmethod
    def assert_can_send_as_view_once(message_type: str, file) -> None:
        if message_type not in VIEW_ONCE_TYPES:
            raise ValueError("View once is only supported for images and videos.")
        if not file:
            raise ValueError("View once requires a media file.")

    @staticmethod
    def is_opened(message: Message) -> bool:
        return message.view_once_opened_at is not None

    @staticmethod
    def viewer_may_see_file(message: Message, viewer: User | None) -> bool:
        """Whether `file_url` should be included in a normal list/detail payload."""
        if message.is_deleted or not message.file:
            return False
        if not message.is_view_once:
            return True
        if viewer is None:
            return False
        if viewer.id == message.sender_id and not ViewOnceService.is_opened(message):
            return True
        return False

    @staticmethod
    def open_and_return_url(message: Message, user: User, request=None) -> tuple[Message, str]:
        """Open view-once: return one-time absolute URL, then permanently clear the file."""
        if message.is_deleted:
            raise ValueError("Message was deleted.")
        if not message.is_view_once:
            raise ValueError("This message is not view once.")
        if message.message_type not in VIEW_ONCE_TYPES:
            raise ValueError("Only photos and videos support view once.")
        if user.id == message.sender_id:
            raise PermissionError("Sender cannot open their own view once media this way.")
        if not Conversation.objects.filter(id=message.conversation_id, participants=user).exists():
            raise PermissionError("Access denied.")
        if ViewOnceService.is_opened(message):
            raise ValueError("This media was already opened.")
        if not message.file:
            raise ValueError("Media is no longer available.")

        relative = message.file.url
        url = request.build_absolute_uri(relative) if request else relative

        message.view_once_opened_at = timezone.now()
        message.view_once_opened_by = user
        message.file.delete(save=False)
        message.file = None
        message.file_size = 0
        message.save(
            update_fields=[
                "view_once_opened_at",
                "view_once_opened_by",
                "file",
                "file_size",
                "updated_at",
            ]
        )
        refreshed = (
            Message.objects.select_related(
                "sender", "reply_to", "reply_to__sender", "view_once_opened_by"
            )
            .prefetch_related("reactions__user", "mention_links__user")
            .get(id=message.id)
        )
        return refreshed, url
