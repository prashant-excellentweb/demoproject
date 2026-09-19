from __future__ import annotations

from apps.users.models import PrivacyVisibility, User


class PrivacyService:
    """Enforce profile / last-seen / status visibility between users."""

    @staticmethod
    def _contact_cache(context: dict | None) -> dict[tuple[int, int], bool]:
        if context is None:
            return {}
        cache = context.setdefault("_privacy_contact_cache", {})
        return cache

    @staticmethod
    def are_contacts(viewer: User, owner: User, *, context: dict | None = None) -> bool:
        """True when viewer and owner share at least one conversation."""
        if viewer.id == owner.id:
            return True
        cache = PrivacyService._contact_cache(context)
        key = (viewer.id, owner.id)
        if key in cache:
            return cache[key]
        result = (
            User.objects.filter(id=owner.id, conversations__participants=viewer)
            .distinct()
            .exists()
        )
        cache[key] = result
        cache[(owner.id, viewer.id)] = result
        return result

    @staticmethod
    def can_view(
        viewer: User | None,
        owner: User,
        setting: str,
        *,
        is_contact: bool | None = None,
        context: dict | None = None,
    ) -> bool:
        """
        Return whether `viewer` may see a field owned by `owner`.

        Owner always sees their own data. Missing viewer → nobody can see.
        """
        if viewer is None:
            return False
        if viewer.id == owner.id:
            return True
        if setting == PrivacyVisibility.EVERYONE:
            return True
        if setting == PrivacyVisibility.NOBODY:
            return False
        if is_contact is None:
            is_contact = PrivacyService.are_contacts(viewer, owner, context=context)
        return bool(is_contact)

    @staticmethod
    def apply_to_public_dict(
        data: dict,
        *,
        owner: User,
        viewer: User | None,
        is_contact: bool | None = None,
        context: dict | None = None,
    ) -> dict:
        """Redact avatar_url / about / last_seen / is_online on a public user payload."""
        if viewer is not None and viewer.id == owner.id:
            return data

        if is_contact is None and viewer is not None:
            is_contact = PrivacyService.are_contacts(viewer, owner, context=context)

        if not PrivacyService.can_view(
            viewer, owner, owner.profile_photo_privacy, is_contact=is_contact, context=context
        ):
            data["avatar_url"] = None
        if not PrivacyService.can_view(
            viewer, owner, owner.about_privacy, is_contact=is_contact, context=context
        ):
            data["about"] = ""
        if not PrivacyService.can_view(
            viewer, owner, owner.last_seen_privacy, is_contact=is_contact, context=context
        ):
            data["is_online"] = False
            data["last_seen"] = None
        return data
