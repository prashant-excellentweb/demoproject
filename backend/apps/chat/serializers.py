from rest_framework import serializers

from apps.chat.models import Conversation, Message, MessageDraft
from apps.users.serializers import UserPublicSerializer

ALLOWED_REACTIONS = ("👍", "❤️", "😂", "😮", "😢", "🙏", "🔥", "👏")

# Quoted preview text is trimmed — clients only render one or two lines.
REPLY_SNIPPET_LENGTH = 120


class MessageQuoteSerializer(serializers.ModelSerializer):
    """Lightweight quoted message shown above an inline reply."""

    sender_id = serializers.IntegerField(read_only=True)
    sender_name = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            "id",
            "sender_id",
            "sender_name",
            "message_type",
            "content",
            "file_name",
            "is_deleted",
        )

    def get_sender_name(self, obj):
        return obj.sender.display_name or obj.sender.phone_number

    def get_content(self, obj):
        if obj.is_deleted:
            return ""
        return obj.content[:REPLY_SNIPPET_LENGTH]


class MessageSerializer(serializers.ModelSerializer):
    sender = UserPublicSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()
    my_reaction = serializers.SerializerMethodField()
    reply_to = MessageQuoteSerializer(read_only=True)
    is_edited = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            "id",
            "conversation",
            "sender",
            "message_type",
            "content",
            "file",
            "file_url",
            "file_name",
            "file_size",
            "reply_to",
            "is_forwarded",
            "forwarded_from",
            "is_read",
            "is_deleted",
            "deleted_at",
            "is_edited",
            "edited_at",
            "reactions",
            "my_reaction",
            "created_at",
        )
        read_only_fields = (
            "id",
            "sender",
            "reply_to",
            "is_forwarded",
            "forwarded_from",
            "is_read",
            "is_deleted",
            "deleted_at",
            "is_edited",
            "edited_at",
            "created_at",
            "file_size",
        )

    def get_file_url(self, obj):
        if obj.is_deleted or not obj.file:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url

    def get_reactions(self, obj):
        if obj.is_deleted:
            return []
        grouped: dict[str, dict] = {}
        for reaction in obj.reactions.all():
            entry = grouped.setdefault(
                reaction.emoji,
                {"emoji": reaction.emoji, "count": 0, "user_ids": []},
            )
            entry["count"] += 1
            entry["user_ids"].append(reaction.user_id)
        return list(grouped.values())

    def get_my_reaction(self, obj):
        if obj.is_deleted:
            return None
        request = self.context.get("request")
        if not request or not getattr(request, "user", None) or not request.user.is_authenticated:
            return None
        for reaction in obj.reactions.all():
            if reaction.user_id == request.user.id:
                return reaction.emoji
        return None

    def get_is_edited(self, obj):
        return obj.edited_at is not None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_deleted:
            data["content"] = ""
            data["file"] = None
            data["file_url"] = None
            data["file_name"] = ""
            data["file_size"] = 0
            data["reactions"] = []
            data["my_reaction"] = None
            data["reply_to"] = None
        return data


class ReactToMessageSerializer(serializers.Serializer):
    emoji = serializers.CharField(max_length=16)

    def validate_emoji(self, value):
        value = (value or "").strip()
        if value not in ALLOWED_REACTIONS:
            raise serializers.ValidationError(
                f"Unsupported reaction. Allowed: {', '.join(ALLOWED_REACTIONS)}"
            )
        return value


class ConversationActionSerializer(serializers.Serializer):
    """Shared body for archive/block/pin endpoints."""

    action = serializers.ChoiceField(
        choices=("archive", "unarchive", "block", "unblock", "pin", "unpin")
    )


class DeleteMessageSerializer(serializers.Serializer):
    delete_for = serializers.ChoiceField(
        choices=("me", "everyone"),
        help_text="'me' = hide only for you; 'everyone' = delete for all participants",
    )


class ConversationSerializer(serializers.ModelSerializer):
    participants = UserPublicSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True, default=0)
    group_avatar_url = serializers.SerializerMethodField()
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    is_admin = serializers.SerializerMethodField()
    is_favourite = serializers.SerializerMethodField()
    is_archived = serializers.SerializerMethodField()
    is_blocked = serializers.SerializerMethodField()
    is_pinned = serializers.SerializerMethodField()
    draft = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            "id",
            "participants",
            "is_group",
            "group_name",
            "group_avatar",
            "group_avatar_url",
            "created_by",
            "is_admin",
            "is_favourite",
            "is_archived",
            "is_blocked",
            "is_pinned",
            "draft",
            "last_message",
            "unread_count",
            "created_at",
            "updated_at",
        )

    def get_is_admin(self, obj):
        request = self.context.get("request")
        if not request or not obj.is_group:
            return False
        return obj.is_group_admin(request.user)

    def get_is_favourite(self, obj):
        if hasattr(obj, "is_favourite"):
            return bool(obj.is_favourite)
        request = self.context.get("request")
        if not request or not getattr(request, "user", None) or not request.user.is_authenticated:
            return False
        return obj.favourited_by.filter(user=request.user).exists()

    def get_is_archived(self, obj):
        if hasattr(obj, "is_archived"):
            return bool(obj.is_archived)
        request = self.context.get("request")
        if not request or not getattr(request, "user", None) or not request.user.is_authenticated:
            return False
        return obj.archived_by.filter(user=request.user).exists()

    def get_is_blocked(self, obj):
        if hasattr(obj, "is_blocked"):
            return bool(obj.is_blocked)
        request = self.context.get("request")
        if not request or not getattr(request, "user", None) or not request.user.is_authenticated:
            return False
        return obj.blocked_by.filter(user=request.user).exists()

    def get_is_pinned(self, obj):
        if hasattr(obj, "is_pinned"):
            return bool(obj.is_pinned)
        request = self.context.get("request")
        if not request or not getattr(request, "user", None) or not request.user.is_authenticated:
            return False
        return obj.pinned_by.filter(user=request.user).exists()

    def get_draft(self, obj):
        """Current user's unsent draft, or None. Uses the `user_drafts` prefetch."""
        drafts = getattr(obj, "user_drafts", None)
        if drafts is not None:
            draft = drafts[0] if drafts else None
        else:
            request = self.context.get("request")
            if not request or not getattr(request, "user", None) or not request.user.is_authenticated:
                return None
            draft = obj.drafts.select_related("reply_to", "reply_to__sender").filter(
                user=request.user
            ).first()
        if not draft or not draft.content.strip():
            return None
        return MessageDraftSerializer(draft, context=self.context).data

    def get_last_message(self, obj):
        latest = getattr(obj, "latest_messages", None)
        if latest:
            msg = latest[0]
            return MessageSerializer(msg, context=self.context).data
        last = obj.messages.select_related("sender").order_by("-created_at").first()
        if last:
            return MessageSerializer(last, context=self.context).data
        return None

    def get_group_avatar_url(self, obj):
        if obj.group_avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.group_avatar.url)
            return obj.group_avatar.url
        return None


class CreateDirectChatSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()


class CreateGroupSerializer(serializers.Serializer):
    group_name = serializers.CharField(max_length=100, min_length=2)
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
    )

    def validate_group_name(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Group name must be at least 2 characters.")
        return value

    def validate_participant_ids(self, value):
        return list(dict.fromkeys(value))


class UpdateGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ("group_name", "group_avatar")

    def validate_group_name(self, value):
        value = (value or "").strip()
        if len(value) < 2:
            raise serializers.ValidationError("Group name must be at least 2 characters.")
        return value


class ForwardMessageSerializer(serializers.Serializer):
    conversation_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=10,
        help_text="Target chats to forward this message into (max 10).",
    )

    def validate_conversation_ids(self, value):
        return list(dict.fromkeys(value))


class MessageDraftSerializer(serializers.ModelSerializer):
    reply_to = MessageQuoteSerializer(read_only=True)

    class Meta:
        model = MessageDraft
        fields = ("conversation", "content", "reply_to", "updated_at")
        read_only_fields = fields


class SaveDraftSerializer(serializers.Serializer):
    content = serializers.CharField(allow_blank=True, max_length=10000)
    reply_to_id = serializers.IntegerField(required=False, allow_null=True)


class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField(required=False, allow_blank=True, default="")
    message_type = serializers.ChoiceField(
        choices=Message.MessageType.choices,
        default=Message.MessageType.TEXT,
    )
    file = serializers.FileField(required=False, allow_null=True)
    reply_to_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="ID of the message being quoted (inline reply).",
    )

    def validate(self, data):
        msg_type = data.get("message_type", Message.MessageType.TEXT)
        content = data.get("content", "")
        file = data.get("file")
        if msg_type == Message.MessageType.TEXT and not content.strip():
            raise serializers.ValidationError("Text messages require content.")
        if msg_type != Message.MessageType.TEXT and not file:
            raise serializers.ValidationError("Media messages require a file.")
        return data


class EditMessageSerializer(serializers.Serializer):
    content = serializers.CharField(
        max_length=10000,
        help_text="Replacement text. Empty is rejected for text messages.",
    )

    def validate_content(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Edited text cannot be empty.")
        return value


class ConversationSearchSerializer(serializers.ModelSerializer):
    """Compact chat summary attached to a search hit (avoids full inbox payload)."""

    group_avatar_url = serializers.SerializerMethodField()
    participants = UserPublicSerializer(many=True, read_only=True)
    name = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            "id",
            "is_group",
            "group_name",
            "group_avatar_url",
            "participants",
            "name",
        )

    def get_group_avatar_url(self, obj):
        if obj.group_avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.group_avatar.url)
            return obj.group_avatar.url
        return None

    def get_name(self, obj):
        if obj.is_group:
            return obj.group_name or "Group"
        request = self.context.get("request")
        viewer_id = getattr(getattr(request, "user", None), "id", None)
        for participant in obj.participants.all():
            if participant.id != viewer_id:
                return participant.display_name or participant.phone_number
        return "Chat"


class MessageSearchHitSerializer(serializers.ModelSerializer):
    sender = UserPublicSerializer(read_only=True)
    snippet = serializers.SerializerMethodField()
    chat = ConversationSearchSerializer(source="conversation", read_only=True)

    class Meta:
        model = Message
        fields = (
            "id",
            "conversation",
            "sender",
            "message_type",
            "content",
            "file_name",
            "snippet",
            "created_at",
            "chat",
        )

    def get_snippet(self, obj):
        query = (self.context.get("query") or "").strip()
        text = obj.content or obj.file_name or ""
        if not query:
            return text[:180]
        lower = text.lower()
        idx = lower.find(query.lower())
        if idx < 0:
            return text[:180]
        start = max(0, idx - 40)
        end = min(len(text), idx + len(query) + 80)
        prefix = "…" if start else ""
        suffix = "…" if end < len(text) else ""
        return f"{prefix}{text[start:end]}{suffix}"
