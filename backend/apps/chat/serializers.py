from rest_framework import serializers

from apps.chat.models import Conversation, Message
from apps.users.serializers import UserPublicSerializer


class MessageSerializer(serializers.ModelSerializer):
    sender = UserPublicSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()

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
            "created_at",
        )
        read_only_fields = ("id", "sender", "is_read", "created_at", "file_size")

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class ConversationSerializer(serializers.ModelSerializer):
    participants = UserPublicSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True, default=0)
    group_avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = (
            "id",
            "participants",
            "is_group",
            "group_name",
            "group_avatar",
            "group_avatar_url",
            "last_message",
            "unread_count",
            "created_at",
            "updated_at",
        )

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
    group_name = serializers.CharField(max_length=100)
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
    )


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
