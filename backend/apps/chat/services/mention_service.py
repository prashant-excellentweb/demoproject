from __future__ import annotations

import json
import re

from apps.chat.models import Conversation, Message, MessageMention
from apps.users.models import User

MAX_MENTIONS = 20
EVERYONE_TOKENS = ("everyone", "all")


class MentionService:
    """Resolve and persist @mentions for group messages."""

    @staticmethod
    def assert_can_post(conversation: Conversation, user: User) -> None:
        if (
            conversation.is_group
            and conversation.admins_only_messages
            and not conversation.is_group_admin(user)
        ):
            raise PermissionError("Only admins can send messages in this group.")

    @staticmethod
    def parse_id_list(raw) -> list[int]:
        if raw is None or raw == "":
            return []
        if isinstance(raw, list):
            values = raw
        elif isinstance(raw, str):
            text = raw.strip()
            if not text:
                return []
            if text.startswith("["):
                try:
                    values = json.loads(text)
                except json.JSONDecodeError:
                    values = [part.strip() for part in text.split(",")]
            else:
                values = [part.strip() for part in text.split(",")]
        else:
            values = [raw]
        ids: list[int] = []
        for item in values:
            try:
                ids.append(int(item))
            except (TypeError, ValueError):
                continue
        return list(dict.fromkeys(ids))

    @staticmethod
    def resolve(
        conversation: Conversation,
        sender: User,
        *,
        mentioned_user_ids: list[int] | None = None,
        mention_everyone: bool = False,
        content: str = "",
    ) -> tuple[list[User], bool]:
        if not conversation.is_group:
            return [], False

        members = list(conversation.participants.exclude(id=sender.id))
        if not members:
            return [], False

        everyone = bool(mention_everyone)
        if not everyone:
            lowered = (content or "").lower()
            everyone = any(re.search(rf"(^|\s)@{token}\b", lowered) for token in EVERYONE_TOKENS)

        if everyone:
            return members[:MAX_MENTIONS], True

        selected: dict[int, User] = {user.id: user for user in members}
        resolved: dict[int, User] = {}
        for user_id in mentioned_user_ids or []:
            if user_id in selected:
                resolved[user_id] = selected[user_id]

        # Also pick up typed @DisplayName tokens that the client did not send as IDs.
        tokens = re.findall(r"@([^\s@]{1,40})", content or "")
        if tokens:
            by_name = {user.display_name.strip().lower(): user for user in members if user.display_name.strip()}
            by_first = {}
            for user in members:
                first = (user.display_name or "").strip().split()
                if first:
                    by_first.setdefault(first[0].lower(), user)
            for token in tokens:
                key = token.lower()
                if key in EVERYONE_TOKENS:
                    return members[:MAX_MENTIONS], True
                match = by_name.get(key) or by_first.get(key)
                if match:
                    resolved[match.id] = match

        return list(resolved.values())[:MAX_MENTIONS], False

    @staticmethod
    def attach(message: Message, users: list[User], mention_everyone: bool = False) -> Message:
        if message.mention_everyone != mention_everyone:
            message.mention_everyone = mention_everyone
            message.save(update_fields=["mention_everyone"])
        if users:
            MessageMention.objects.bulk_create(
                [MessageMention(message=message, user=user) for user in users],
                ignore_conflicts=True,
            )
        return (
            Message.objects.select_related("sender", "reply_to", "reply_to__sender")
            .prefetch_related("reactions__user", "mention_links__user")
            .get(id=message.id)
        )
