from django.urls import path
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.serializers import TokenRefreshRequestSerializer, TokenRefreshResponseSerializer
from apps.users.views import (
    LogoutView,
    ProfileView,
    SendOTPView,
    UserDetailView,
    UserSearchView,
    VerifyOTPView,
)

TokenRefreshView = extend_schema(
    tags=["Auth"],
    summary="Refresh JWT access token",
    description="Exchange a valid refresh token for a new access token.",
    request=TokenRefreshRequestSerializer,
    responses={200: TokenRefreshResponseSerializer},
)(TokenRefreshView)

urlpatterns = [
    path("send-otp/", SendOTPView.as_view(), name="send-otp"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("search/", UserSearchView.as_view(), name="user-search"),
    path("users/<int:user_id>/", UserDetailView.as_view(), name="user-detail"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
