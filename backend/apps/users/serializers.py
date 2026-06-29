import re

from rest_framework import serializers

from apps.users.models import User, normalize_phone


class UserSerializer(serializers.ModelSerializer):
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
            "date_joined",
        )
        read_only_fields = ("id", "phone_number", "is_online", "last_seen", "date_joined")

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None


class UserPublicSerializer(serializers.ModelSerializer):
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
    class Meta:
        model = User
        fields = ("display_name", "about", "avatar")


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