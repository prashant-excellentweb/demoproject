from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from apps.stories.models import Status, StatusView
from apps.users.serializers import UserPublicSerializer


class StatusSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(read_only=True)
    media_url = serializers.SerializerMethodField()
    is_viewed = serializers.SerializerMethodField()
    view_count = serializers.SerializerMethodField()

    class Meta:
        model = Status
        fields = (
            "id",
            "user",
            "status_type",
            "content",
            "media",
            "media_url",
            "background_color",
            "created_at",
            "expires_at",
            "is_viewed",
            "view_count",
        )
        read_only_fields = ("id", "created_at", "expires_at")

    def get_media_url(self, obj):
        if obj.media:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.media.url)
            return obj.media.url
        return None

    def get_is_viewed(self, obj):
        user_views = getattr(obj, "user_views", None)
        if user_views is not None:
            return len(user_views) > 0
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return StatusView.objects.filter(status=obj, viewer=request.user).exists()
        return False

    def get_view_count(self, obj):
        return obj.views.count()


class CreateStatusSerializer(serializers.Serializer):
    status_type = serializers.ChoiceField(choices=Status.StatusType.choices)
    content = serializers.CharField(required=False, allow_blank=True, default="")
    media = serializers.FileField(required=False, allow_null=True)
    background_color = serializers.CharField(max_length=7, required=False, default="#075E54")

    def validate(self, data):
        status_type = data["status_type"]
        if status_type == Status.StatusType.TEXT and not data.get("content", "").strip():
            raise serializers.ValidationError("Text status requires content.")
        if status_type in (Status.StatusType.IMAGE, Status.StatusType.VIDEO) and not data.get("media"):
            raise serializers.ValidationError("Media status requires a file.")
        return data


class StatusGroupSerializer(serializers.Serializer):
    """Grouped statuses by user for the stories UI."""

    user = UserPublicSerializer()
    statuses = StatusSerializer(many=True)
    has_unviewed = serializers.BooleanField()
    latest_at = serializers.DateTimeField()


class StatusFeedResponseSerializer(serializers.Serializer):
    my_statuses = StatusSerializer(many=True)
    contacts = StatusGroupSerializer(many=True)
