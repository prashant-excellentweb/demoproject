from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView

from apps.common.responses import api_error, api_success
from apps.users.models import OTPVerification, User, UserReport
from apps.users.serializers import (
    ProfileUpdateSerializer,
    ReportUserSerializer,
    SendOTPSerializer,
    UserPublicSerializer,
    UserSerializer,
    VerifyOTPSerializer,
)
from apps.users.services.account_service import AccountService
from apps.users.services.sms_service import SMSService


class SendOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(tags=["Auth"], summary="Send OTP via SMS", request=SendOTPSerializer)
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone_number"]

        otp_record = OTPVerification.generate_otp(phone)
        sent = SMSService.send_otp(phone, otp_record.otp_code)
        if not sent:
            return api_error(
                message="Failed to send SMS. Try again later.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return api_success(
            data={"phone_number": phone},
            message="OTP sent successfully.",
        )


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(tags=["Auth"], summary="Verify OTP and login", request=VerifyOTPSerializer)
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone_number"]
        code = serializer.validated_data["otp_code"]

        otp_record = (
            OTPVerification.objects.filter(phone_number=phone, is_verified=False)
            .order_by("-created_at")
            .first()
        )
        static_otp = getattr(settings, "STATIC_OTP", "")
        otp_valid = static_otp and code == static_otp
        if not otp_valid and (not otp_record or not otp_record.verify(code)):
            return api_error(message="Invalid or expired OTP.", status_code=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(phone_number=phone, is_active=True)
            created = False
        except User.DoesNotExist:
            user = User.objects.create_user(phone_number=phone)
            created = True

        user.is_online = True
        user.last_seen = timezone.now()
        user.save(update_fields=["is_online", "last_seen"])

        refresh = RefreshToken.for_user(user)
        user_data = UserSerializer(user, context={"request": request}).data
        return api_success(
            data={
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": user_data,
                "is_new_user": created,
                "requires_profile_setup": not user.profile_setup_complete,
            },
            message="Login successful.",
        )


class TokenRefreshView(BaseTokenRefreshView):
    @extend_schema(tags=["Auth"], summary="Refresh JWT access token")
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code >= 400:
            return api_error(
                message="Token refresh failed.",
                data=response.data,
                status_code=response.status_code,
            )
        return api_success(data=response.data, message="Token refreshed successfully.")


class ProfileView(APIView):
    @extend_schema(tags=["Auth"], summary="Get current user profile")
    def get(self, request):
        return api_success(
            data=UserSerializer(request.user, context={"request": request}).data,
            message="Profile fetched successfully.",
        )

    @extend_schema(tags=["Auth"], summary="Update profile", request=ProfileUpdateSerializer)
    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_success(
            data=UserSerializer(request.user, context={"request": request}).data,
            message="Profile updated successfully.",
        )

    @extend_schema(tags=["Auth"], summary="Delete account (soft-delete)")
    def delete(self, request):
        AccountService.delete_account(request.user)
        return api_success(message="Account deleted successfully.", data=None)


class UserSearchView(APIView):
    @extend_schema(
        tags=["Auth"],
        summary="Search users",
        parameters=[OpenApiParameter(name="q", type=str, location=OpenApiParameter.QUERY, required=True)],
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return api_success(data=[], message="Search query too short.")
        users = (
            User.objects.filter(is_active=True)
            .filter(Q(display_name__icontains=query) | Q(phone_number__icontains=query))
            .exclude(id=request.user.id)[:20]
        )
        return api_success(
            data=UserPublicSerializer(users, many=True, context={"request": request}).data,
            message="Users fetched successfully.",
        )


class UserDetailView(APIView):
    @extend_schema(tags=["Auth"], summary="Get user by ID")
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return api_error(message="User not found.", status_code=status.HTTP_404_NOT_FOUND)
        return api_success(
            data=UserPublicSerializer(user, context={"request": request}).data,
            message="User fetched successfully.",
        )


class ReportUserView(APIView):
    @extend_schema(tags=["Auth"], summary="Report a user", request=ReportUserSerializer)
    def post(self, request, user_id):
        if user_id == request.user.id:
            return api_error(
                message="You cannot report yourself.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            reported = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return api_error(message="User not found.", status_code=status.HTTP_404_NOT_FOUND)

        serializer = ReportUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = None
        conversation_id = serializer.validated_data.get("conversation_id")
        if conversation_id:
            from apps.chat.models import Conversation
            from apps.chat.repositories.conversation_repository import ConversationRepository

            try:
                conversation = Conversation.objects.get(id=conversation_id)
            except Conversation.DoesNotExist:
                return api_error(message="Conversation not found.", status_code=status.HTTP_404_NOT_FOUND)
            if not ConversationRepository.user_in_conversation(conversation, request.user):
                return api_error(message="Access denied.", status_code=status.HTTP_403_FORBIDDEN)

        report = UserReport.objects.create(
            reporter=request.user,
            reported_user=reported,
            conversation=conversation,
            reason=serializer.validated_data["reason"],
            details=serializer.validated_data.get("details", ""),
        )
        return api_success(
            data={"id": report.id, "reason": report.reason},
            message="Report submitted. Thank you.",
            status_code=status.HTTP_201_CREATED,
        )


class LogoutView(APIView):
    @extend_schema(tags=["Auth"], summary="Logout")
    def post(self, request):
        request.user.is_online = False
        request.user.last_seen = timezone.now()
        request.user.save(update_fields=["is_online", "last_seen"])
        return api_success(message="Logged out successfully.", data=None)
