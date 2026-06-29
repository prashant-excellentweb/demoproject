from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.users.models import OTPVerification, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("phone_number", "display_name", "is_online", "last_seen", "is_staff")
    search_fields = ("phone_number", "display_name")
    ordering = ("-date_joined",)
    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        ("Profile", {"fields": ("display_name", "about", "avatar")}),
        ("Status", {"fields": ("is_online", "last_seen")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("phone_number", "display_name", "password1", "password2")}),
    )


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "otp_code", "is_verified", "attempts", "created_at")
    list_filter = ("is_verified",)
