from django.contrib import admin

from apps.stories.models import Status, StatusView


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status_type", "created_at", "expires_at")
    list_filter = ("status_type",)


@admin.register(StatusView)
class StatusViewAdmin(admin.ModelAdmin):
    list_display = ("status", "viewer", "viewed_at")
