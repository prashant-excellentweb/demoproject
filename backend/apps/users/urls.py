from django.urls import path

from apps.users.views import (
    LogoutView,
    ProfileView,
    ReportUserView,
    SendOTPView,
    TokenRefreshView,
    UserDetailView,
    UserSearchView,
    VerifyOTPView,
)

urlpatterns = [
    path("send-otp/", SendOTPView.as_view(), name="send-otp"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("search/", UserSearchView.as_view(), name="user-search"),
    path("users/<int:user_id>/", UserDetailView.as_view(), name="user-detail"),
    path("users/<int:user_id>/report/", ReportUserView.as_view(), name="report-user"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
