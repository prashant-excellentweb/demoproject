from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from apps.users.models import User
from apps.users.services.privacy_service import PrivacyService


class PresenceService:
    """Broadcast online / last-seen changes to conversation contacts."""

    @staticmethod
    def set_and_broadcast(user: User, online: bool) -> None:
        user.is_online = online
        user.last_seen = timezone.now()
        user.save(update_fields=["is_online", "last_seen"])
        PresenceService.broadcast(user)

    @staticmethod
    def broadcast(user: User) -> None:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        contact_ids = list(
            User.objects.filter(conversations__participants=user)
            .exclude(id=user.id)
            .distinct()
            .values_list("id", flat=True)
        )
        if not contact_ids:
            return

        contacts = {u.id: u for u in User.objects.filter(id__in=contact_ids)}
        for contact_id, contact in contacts.items():
            payload = {
                "user_id": user.id,
                "is_online": user.is_online,
                "last_seen": user.last_seen.isoformat() if user.last_seen else None,
            }
            # Respect last-seen privacy for each viewer.
            redacted = PrivacyService.apply_to_public_dict(
                {
                    "is_online": payload["is_online"],
                    "last_seen": payload["last_seen"],
                },
                owner=user,
                viewer=contact,
            )
            async_to_sync(channel_layer.group_send)(
                f"user_{contact_id}",
                {
                    "type": "presence_update",
                    "user_id": user.id,
                    "is_online": redacted.get("is_online", False),
                    "last_seen": redacted.get("last_seen"),
                },
            )
