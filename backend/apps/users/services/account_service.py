from django.db import transaction
from django.utils import timezone

from apps.users.models import User


class AccountService:
    @staticmethod
    @transaction.atomic
    def delete_account(user: User) -> None:
        """Soft-delete: deactivate account and free the phone number for re-registration."""
        ts = int(timezone.now().timestamp())
        marker = f"deleted_{user.id}_{ts}"
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
        user.is_active = False
        user.is_online = False
        user.last_seen = timezone.now()
        user.phone_number = marker
        user.username = marker
        user.display_name = "Deleted Account"
        user.about = ""
        user.profile_setup_complete = False
        user.save(
            update_fields=[
                "is_active",
                "is_online",
                "last_seen",
                "phone_number",
                "username",
                "display_name",
                "about",
                "avatar",
                "profile_setup_complete",
            ]
        )
