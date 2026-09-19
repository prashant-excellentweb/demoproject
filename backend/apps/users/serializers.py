import re

from rest_framework import serializers

from apps.users.models import PrivacyVisibility, User, normalize_phone
from apps.users.services.privacy_service import PrivacyService

PRIVACY_CHOICES = [c.value for c in PrivacyVisibility]


class UserSerializer(serializers.ModelSerializer):
    """Full profile for the authenticated owner (includes privacy prefs)."""

    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "phone_number",
            "display_name",
            "about",
            "avatar",
            "avatar_url",
            "is_online",
            "last_seen",
            "profile_setup_complete",
            "date_joined",
            "profile_photo_privacy",
            "about_privacy",
            "last_seen_privacy",
            "status_privacy",
        )
        read_only_fields = (
            "id",
            "phone_number",
            "is_online",
            "last_seen",
            "profile_setup_complete",
            "date_joined",
        )

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None


class UserPublicSerializer(serializers.ModelSerializer):
    """Public user payload with privacy redaction for the requesting viewer."""

    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "phone_number",
            "display_name",
            "about",
            "avatar_url",
            "is_online",
            "last_seen",
        )

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        viewer = getattr(request, "user", None) if request else None
        if viewer is not None and not getattr(viewer, "is_authenticated", False):
            viewer = None
        return PrivacyService.apply_to_public_dict(
            data, owner=instance, viewer=viewer, context=self.context
        )


class SendOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)

    def validate_phone_number(self, value):
        normalized = normalize_phone(value)
        if len(re.sub(r"\D", "", normalized)) < 10:
            raise serializers.ValidationError("Enter a valid phone number.")
        return normalized


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    otp_code = serializers.CharField(min_length=6, max_length=6)

    def validate_phone_number(self, value):
        return normalize_phone(value)


class ProfileUpdateSerializer(serializers.ModelSerializer):
    profile_photo_privacy = serializers.ChoiceField(choices=PRIVACY_CHOICES, required=False)
    about_privacy = serializers.ChoiceField(choices=PRIVACY_CHOICES, required=False)
    last_seen_privacy = serializers.ChoiceField(choices=PRIVACY_CHOICES, required=False)
    status_privacy = serializers.ChoiceField(choices=PRIVACY_CHOICES, required=False)

    class Meta:
        model = User
        fields = (
            "display_name",
            "about",
            "avatar",
            "profile_photo_privacy",
            "about_privacy",
            "last_seen_privacy",
            "status_privacy",
        )

    def validate_display_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Display name is required.")
        if len(value) < 2:
            raise serializers.ValidationError("Display name must be at least 2 characters.")
        return value

    def update(self, instance, validated_data):
        user = super().update(instance, validated_data)
        if user.display_name.strip():
            user.profile_setup_complete = True
            user.save(update_fields=["profile_setup_complete"])
        return user


class ReportUserSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(choices=["spam", "harassment", "inappropriate", "fake", "other"])
    details = serializers.CharField(required=False, allow_blank=True, max_length=1000, default="")
    conversation_id = serializers.IntegerField(required=False, allow_null=True)


class SendOTPResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    phone_number = serializers.CharField()


class AuthTokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="JWT access token — use in Authorization header")
    refresh = serializers.CharField(help_text="JWT refresh token")
    user = UserSerializer()
    is_new_user = serializers.BooleanField()


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class TokenRefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class TokenRefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField(required=False)
