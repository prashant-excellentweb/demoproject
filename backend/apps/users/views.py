from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import OTPVerification, User
from apps.users.serializers import (
    AuthTokenResponseSerializer,
    DetailResponseSerializer,
    ProfileUpdateSerializer,
    SendOTPResponseSerializer,
    SendOTPSerializer,
    UserPublicSerializer,
    UserSerializer,
    VerifyOTPSerializer,
)
from apps.users.services.sms_service import SMSService


class SendOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["Auth"],
        summary="Send OTP via SMS",
        description="Send a 6-digit OTP to the given phone number. In dev mode OTP is printed in server logs.",
        request=SendOTPSerializer,
        responses={200: SendOTPResponseSerializer, 503: DetailResponseSerializer},
    )
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone_number"]

        otp_record = OTPVerification.generate_otp(phone)
        sent = SMSService.send_otp(phone, otp_record.otp_code)
        if not sent:
            return Response(
                {"detail": "Failed to send SMS. Try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"detail": "OTP sent successfully.", "phone_number": phone})


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["Auth"],
        summary="Verify OTP and login",
        description="Verify OTP code. Returns JWT tokens and user profile. Creates account if new phone number.",
        request=VerifyOTPSerializer,
        responses={200: AuthTokenResponseSerializer, 400: DetailResponseSerializer},
    )
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
            return Response(
                {"detail": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(phone_number=phone)
            created = False
        except User.DoesNotExist:
            user = User.objects.create_user(phone_number=phone)
            created = True

        user.is_online = True
        user.last_seen = timezone.now()
        user.save(update_fields=["is_online", "last_seen"])

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user, context={"request": request}).data,
                "is_new_user": created,
            }
        )


class ProfileView(APIView):
    @extend_schema(
        tags=["Auth"],
        summary="Get current user profile",
        responses={200: UserSerializer},
    )
    def get(self, request):
        return Response(UserSerializer(request.user, context={"request": request}).data)

    @extend_schema(
        tags=["Auth"],
        summary="Update profile",
        description="Update display name, about, and/or avatar. Use multipart/form-data when uploading avatar.",
        request=ProfileUpdateSerializer,
        responses={200: UserSerializer},
    )
    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user, context={"request": request}).data)


class UserSearchView(APIView):
    @extend_schema(
        tags=["Auth"],
        summary="Search users",
        description="Search registered users by display name or phone number (min 2 characters).",
        parameters=[
            OpenApiParameter(name="q", type=str, location=OpenApiParameter.QUERY, required=True),
        ],
        responses={200: UserPublicSerializer(many=True)},
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response([])
        users = (
            User.objects.filter(display_name__icontains=query)
            | User.objects.filter(phone_number__icontains=query)
        )
        users = users.exclude(id=request.user.id)[:20]
        return Response(
            UserPublicSerializer(users, many=True, context={"request": request}).data
        )


class UserDetailView(APIView):
    @extend_schema(
        tags=["Auth"],
        summary="Get user by ID",
        responses={200: UserPublicSerializer, 404: DetailResponseSerializer},
    )
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(UserPublicSerializer(user, context={"request": request}).data)


class LogoutView(APIView):
    @extend_schema(
        tags=["Auth"],
        summary="Logout",
        description="Marks user as offline and updates last_seen.",
        responses={200: DetailResponseSerializer},
    )
    def post(self, request):
        request.user.is_online = False
        request.user.last_seen = timezone.now()
        request.user.save(update_fields=["is_online", "last_seen"])
        return Response({"detail": "Logged out."})
