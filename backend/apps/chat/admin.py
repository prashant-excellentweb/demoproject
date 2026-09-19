from django.contrib import admin

from apps.chat.models import (
    Conversation,
    ConversationArchive,
    ConversationBlock,
    ConversationFavourite,
    ConversationPin,
    Message,
    MessageDraft,
    MessageHidden,
    MessageReaction,
    MessageStatus,
)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "is_group", "group_name", "created_by", "updated_at")
    filter_horizontal = ("participants",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "conversation",
        "sender",
        "message_type",
        "reply_to",
        "is_forwarded",
        "edited_at",
        "is_read",
        "is_deleted",
        "created_at",
    )
    list_filter = ("message_type", "is_forwarded", "is_read", "is_deleted")


@admin.register(MessageDraft)
class MessageDraftAdmin(admin.ModelAdmin):
    list_display = ("conversation", "user", "updated_at")
    search_fields = ("content",)


@admin.register(MessageStatus)
class MessageStatusAdmin(admin.ModelAdmin):
    list_display = ("message", "user", "is_delivered", "is_read")


@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ("message", "user", "emoji", "created_at")
    list_filter = ("emoji",)


@admin.register(MessageHidden)
class MessageHiddenAdmin(admin.ModelAdmin):
    list_display = ("message", "user", "hidden_at")


@admin.register(ConversationFavourite)
class ConversationFavouriteAdmin(admin.ModelAdmin):
    list_display = ("conversation", "user", "created_at")


@admin.register(ConversationArchive)
class ConversationArchiveAdmin(admin.ModelAdmin):
    list_display = ("conversation", "user", "archived_at")


@admin.register(ConversationBlock)
class ConversationBlockAdmin(admin.ModelAdmin):
    list_display = ("conversation", "user", "blocked_at")


@admin.register(ConversationPin)
class ConversationPinAdmin(admin.ModelAdmin):
    list_display = ("conversation", "user", "pinned_at")
