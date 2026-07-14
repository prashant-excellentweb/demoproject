from rest_framework import serializers

from apps.chat.models import Conversation, Message
from apps.users.serializers import UserPublicSerializer

ALLOWED_REACTIONS = ("👍", "❤️", "😂", "😮", "😢", "🙏", "🔥", "👏")


class MessageSerializer(serializers.ModelSerializer):
    sender = UserPublicSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()
    my_reaction = serializers.SerializerMethodField()

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
            "is_read",
            "is_deleted",
            "deleted_at",
            "reactions",
            "my_reaction",
            "created_at",
        )
        read_only_fields = (
            "id",
            "sender",
            "is_read",
            "is_deleted",
            "deleted_at",
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
    """Shared body for archive/block endpoints."""

    action = serializers.ChoiceField(choices=("archive", "unarchive", "block", "unblock"))


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


class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField(required=False, allow_blank=True, default="")
    message_type = serializers.ChoiceField(
        choices=Message.MessageType.choices,
        default=Message.MessageType.TEXT,
    )
    file = serializers.FileField(required=False, allow_null=True)

    def validate(self, data):
        msg_type = data.get("message_type", Message.MessageType.TEXT)
        content = data.get("content", "")
        file = data.get("file")
        if msg_type == Message.MessageType.TEXT and not content.strip():
            raise serializers.ValidationError("Text messages require content.")
        if msg_type != Message.MessageType.TEXT and not file:
            raise serializers.ValidationError("Media messages require a file.")
        return data
