from django.conf import settings
from django.db import models


class Conversation(models.Model):
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="conversations",
    )
    is_group = models.BooleanField(default=False)
    group_name = models.CharField(max_length=100, blank=True)
    group_avatar = models.ImageField(upload_to="group_avatars/", blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_groups",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["-updated_at"]),
            models.Index(fields=["is_group"]),
        ]

    def __str__(self):
        if self.is_group:
            return self.group_name or f"Group {self.pk}"
        return f"Conversation {self.pk}"

    def is_group_admin(self, user) -> bool:
        if not self.is_group:
            return False
        if self.created_by_id:
            return self.created_by_id == user.id
        admin = self.participants.order_by("id").first()
        return admin is not None and admin.id == user.id


class Message(models.Model):
    class MessageType(models.TextChoices):
        TEXT = "text", "Text"
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        PDF = "pdf", "PDF"
        DOCUMENT = "document", "Document"
        AUDIO = "audio", "Audio"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT,
    )
    content = models.TextField(blank=True)
    file = models.FileField(upload_to="messages/", blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_messages",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["sender", "created_at"]),
            models.Index(fields=["conversation", "is_read"]),
            models.Index(fields=["conversation", "is_deleted"]),
        ]

    def __str__(self):
        return f"{self.sender} - {self.message_type} @ {self.created_at}"


class MessageStatus(models.Model):
    """Per-user read/delivery status for group chats."""

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="statuses")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_delivered = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("message", "user")
        indexes = [
            models.Index(fields=["user", "is_read"]),
        ]


class MessageReaction(models.Model):
    """One emoji reaction per user per message (toggle to remove)."""

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="message_reactions")
    emoji = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("message", "user")
        indexes = [
            models.Index(fields=["message", "emoji"]),
        ]

    def __str__(self):
        return f"{self.user_id} {self.emoji} on message {self.message_id}"


class MessageHidden(models.Model):
    """Per-user 'delete for me' — message stays visible to others."""

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="hidden_for")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hidden_messages")
    hidden_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("message", "user")
        indexes = [
            models.Index(fields=["user", "message"]),
        ]

    def __str__(self):
        return f"user {self.user_id} hid message {self.message_id}"
