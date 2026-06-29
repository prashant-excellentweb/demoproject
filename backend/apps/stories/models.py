from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Status(models.Model):
    """WhatsApp-style status (text, image, or video) that expires after 24 hours."""

    class StatusType(models.TextChoices):
        TEXT = "text", "Text"
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="statuses",
    )
    status_type = models.CharField(max_length=10, choices=StatusType.choices, default=StatusType.TEXT)
    content = models.TextField(blank=True)
    media = models.FileField(upload_to="status/", blank=True, null=True)
    background_color = models.CharField(max_length=7, default="#075E54")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        verbose_name_plural = "statuses"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "expires_at"]),
            models.Index(fields=["expires_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=settings.STORY_EXPIRY_HOURS)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.user} - {self.status_type}"


class StatusView(models.Model):
    status = models.ForeignKey(Status, on_delete=models.CASCADE, related_name="views")
    viewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("status", "viewer")
        indexes = [
            models.Index(fields=["status", "viewer"]),
        ]
