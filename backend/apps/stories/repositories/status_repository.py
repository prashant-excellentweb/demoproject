from django.db.models import Prefetch, Q
from django.utils import timezone

from apps.stories.models import Status, StatusView
from apps.users.models import User


class StatusRepository:
    @staticmethod
    def get_active_statuses():
        now = timezone.now()
        return Status.objects.filter(expires_at__gt=now).select_related("user")

    @staticmethod
    def get_contacts_statuses(user: User):
        """Statuses from users the current user has conversations with."""
        contact_ids = (
            User.objects.filter(conversations__participants=user)
            .exclude(id=user.id)
            .values_list("id", flat=True)
            .distinct()
        )
        now = timezone.now()
        return (
            Status.objects.filter(user_id__in=contact_ids, expires_at__gt=now)
            .select_related("user")
            .prefetch_related(
                Prefetch("views", queryset=StatusView.objects.filter(viewer=user), to_attr="user_views")
            )
            .order_by("-created_at")
        )

    @staticmethod
    def get_my_statuses(user: User):
        now = timezone.now()
        return Status.objects.filter(user=user, expires_at__gt=now).order_by("-created_at")

    @staticmethod
    def mark_viewed(status: Status, viewer: User):
        StatusView.objects.get_or_create(status=status, viewer=viewer)

    @staticmethod
    def cleanup_expired():
        Status.objects.filter(expires_at__lte=timezone.now()).delete()
