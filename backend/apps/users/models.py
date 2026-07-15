import random
import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    return f"+{digits}"


class UserManager(BaseUserManager):
    def create_user(self, phone_number, **extra_fields):
        if not phone_number:
            raise ValueError("Phone number is required")
        phone_number = normalize_phone(phone_number)
        extra_fields.setdefault("profile_setup_complete", False)
        user = self.model(phone_number=phone_number, username=phone_number, **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        phone_number = normalize_phone(phone_number)
        user = self.model(phone_number=phone_number, username=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user


class User(AbstractUser):
    phone_number = models.CharField(max_length=20, unique=True, db_index=True)
    display_name = models.CharField(max_length=100, blank=True)
    about = models.CharField(max_length=255, default="Hey there! I am using ChatApp.")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)
    profile_setup_complete = models.BooleanField(default=False)

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        indexes = [
            models.Index(fields=["phone_number"]),
            models.Index(fields=["display_name"]),
        ]

    def __str__(self):
        return self.display_name or self.phone_number

    def save(self, *args, **kwargs):
        if self.phone_number:
            self.username = self.phone_number
        super().save(*args, **kwargs)

    @property
    def name(self):
        return self.display_name or self.phone_number


class UserReport(models.Model):
    class Reason(models.TextChoices):
        SPAM = "spam", "Spam"
        HARASSMENT = "harassment", "Harassment"
        INAPPROPRIATE = "inappropriate", "Inappropriate content"
        FAKE = "fake", "Fake account"
        OTHER = "other", "Other"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports_filed",
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports_received",
    )
    conversation = models.ForeignKey(
        "chat.Conversation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_reports",
    )
    reason = models.CharField(max_length=32, choices=Reason.choices, default=Reason.OTHER)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["reported_user", "-created_at"]),
            models.Index(fields=["reporter", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.reporter_id} reported {self.reported_user_id} ({self.reason})"


class OTPVerification(models.Model):
    phone_number = models.CharField(max_length=20, db_index=True)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["phone_number", "created_at"]),
        ]

    @classmethod
    def generate_otp(cls, phone_number: str) -> "OTPVerification":
        phone_number = normalize_phone(phone_number)
        cls.objects.filter(phone_number=phone_number, is_verified=False).delete()
        if getattr(settings, "STATIC_OTP", ""):
            otp_code = settings.STATIC_OTP
        else:
            otp_code = str(random.randint(100000, 999999))
        return cls.objects.create(phone_number=phone_number, otp_code=otp_code)

    def is_expired(self) -> bool:
        expiry = self.created_at + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        return timezone.now() > expiry

    def verify(self, code: str) -> bool:
        if self.is_expired():
            return False
        if self.attempts >= 5:
            return False
        self.attempts += 1
        if self.otp_code == code:
            self.is_verified = True
            self.save(update_fields=["is_verified", "attempts"])
            return True
        self.save(update_fields=["attempts"])
        return False
