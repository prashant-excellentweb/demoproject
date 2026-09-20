from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView

from apps.chat.consumers import broadcast_message_deleted, broadcast_message_updated, broadcast_new_message
from apps.chat.models import Conversation, Message
from apps.chat.repositories.conversation_repository import ConversationRepository, MessageRepository
from apps.chat.repositories.draft_repository import DraftRepository
from apps.chat.serializers import (
    ConversationActionSerializer,
    ConversationSerializer,
    CreateDirectChatSerializer,
    CreateGroupSerializer,
    DeleteMessageSerializer,
    EditMessageSerializer,
    ForwardMessageSerializer,
    MessageDraftSerializer,
    MessageSearchHitSerializer,
    MessageSerializer,
    ReactToMessageSerializer,
    SaveDraftSerializer,
    SendMessageSerializer,
    UpdateGroupSerializer,
)
from apps.chat.services.message_search_service import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    MIN_QUERY_LENGTH,
    MessageSearchService,
)
from apps.chat.services.mention_service import MentionService
from apps.chat.services.message_service import MessageService
from apps.common.responses import api_error, api_success
from apps.users.models import User


def _get_user_conversation(request, conversation_id):
    """Fetch a conversation the caller participates in, or an error response."""
    try:
        conv = Conversation.objects.get(id=conversation_id)
    except Conversation.DoesNotExist:
        return None, api_error(message="Conversation not found.", status_code=status.HTTP_404_NOT_FOUND)
    if not ConversationRepository.user_in_conversation(conv, request.user):
        return None, api_error(message="Access denied.", status_code=status.HTTP_403_FORBIDDEN)
    return conv, None


def _get_group_conversation(request, conversation_id):
    try:
        conv = Conversation.objects.get(id=conversation_id, is_group=True)
    except Conversation.DoesNotExist:
        return None, api_error(message="Group not found.", status_code=status.HTTP_404_NOT_FOUND)
    if not ConversationRepository.user_in_conversation(conv, request.user):
        return None, api_error(message="Access denied.", status_code=status.HTTP_403_FORBIDDEN)
    return conv, None


class ConversationListView(APIView):
    @extend_schema(
        tags=["Chat"],
        summary="List conversations",
        description=(
            "Filter with `?filter=all|unread|groups|favourites|archived|blocked`. "
            "Archived chats are excluded from main inbox filters."
        ),
        parameters=[
            OpenApiParameter(
                name="filter",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                enum=["all", "unread", "groups", "favourites", "archived", "blocked"],
                description="Chat list filter tab",
            ),
        ],
    )
    def get(self, request):
        filter_by = request.query_params.get("filter", "all")
        conversations = ConversationRepository.get_user_conversations(request.user, filter_by=filter_by)
        return api_success(
            data=ConversationSerializer(conversations, many=True, context={"request": request}).data,
            message="Conversations fetched successfully.",
        )


def _serialize_user_conversation(request, conversation_id: int) -> dict:
    conversations = ConversationRepository.get_user_conversations(request.user, filter_by="all")
    # Prefer annotated row from inbox; fall back to archived/blocked lookup
    conv = conversations.filter(id=conversation_id).first()
    if not conv:
        for alt in ("archived", "blocked"):
            conv = (
                ConversationRepository.get_user_conversations(request.user, filter_by=alt)
                .filter(id=conversation_id)
                .first()
            )
            if conv:
                break
    if not conv:
        conv = Conversation.objects.get(id=conversation_id)
    return ConversationSerializer(conv, context={"request": request}).data


class ToggleFavouriteView(APIView):
    @extend_schema(tags=["Chat"], summary="Toggle favourite chat")
    def post(self, request, conversation_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return api_error(message="Conversation not found.", status_code=status.HTTP_404_NOT_FOUND)
        if not ConversationRepository.user_in_conversation(conv, request.user):
            return api_error(message="Access denied.", status_code=status.HTTP_403_FORBIDDEN)

        is_favourite = ConversationRepository.toggle_favourite(conv, request.user)
        data = _serialize_user_conversation(request, conversation_id)
        data["is_favourite"] = is_favourite
        return api_success(
            data=data,
            message="Added to favourites." if is_favourite else "Removed from favourites.",
        )


class ArchiveConversationView(APIView):
    @extend_schema(
        tags=["Chat"],
        summary="Archive or unarchive chat",
        request=ConversationActionSerializer,
    )
    def post(self, request, conversation_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return api_error(message="Conversation not found.", status_code=status.HTTP_404_NOT_FOUND)
        if not ConversationRepository.user_in_conversation(conv, request.user):
            return api_error(message="Access denied.", status_code=status.HTTP_403_FORBIDDEN)

        action = request.data.get("action", "archive")
        if action not in ("archive", "unarchive"):
            return api_error(
                message="action must be 'archive' or 'unarchive'.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        is_archived = ConversationRepository.set_archived(conv, request.user, archived=(action == "archive"))
        data = _serialize_user_conversation(request, conversation_id)
        data["is_archived"] = is_archived
        return api_success(
            data=data,
            message="Chat archived." if is_archived else "Chat unarchived.",
        )


class BlockConversationView(APIView):
    @extend_schema(
        tags=["Chat"],
        summary="Block or unblock chat",
        request=ConversationActionSerializer,
    )
    def post(self, request, conversation_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return api_error(message="Conversation not found.", status_code=status.HTTP_404_NOT_FOUND)
        if not ConversationRepository.user_in_conversation(conv, request.user):
            return api_error(message="Access denied.", status_code=status.HTTP_403_FORBIDDEN)

        action = request.data.get("action", "block")
        if action not in ("block", "unblock"):
            return api_error(
                message="action must be 'block' or 'unblock'.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        is_blocked = ConversationRepository.set_blocked(conv, request.user, blocked=(action == "block"))
        data = _serialize_user_conversation(request, conversation_id)
        data["is_blocked"] = is_blocked
        return api_success(
            data=data,
            message="Chat blocked." if is_blocked else "Chat unblocked.",
        )


class PinConversationView(APIView):
    @extend_schema(
        tags=["Chat"],
        summary="Pin or unpin chat",
        request=ConversationActionSerializer,
    )
    def post(self, request, conversation_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return api_error(message="Conversation not found.", status_code=status.HTTP_404_NOT_FOUND)
        if not ConversationRepository.user_in_conversation(conv, request.user):
            return api_error(message="Access denied.", status_code=status.HTTP_403_FORBIDDEN)

        action = request.data.get("action", "pin")
        if action not in ("pin", "unpin"):
            return api_error(
                message="action must be 'pin' or 'unpin'.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        is_pinned = ConversationRepository.set_pinned(conv, request.user, pinned=(action == "pin"))
        data = _serialize_user_conversation(request, conversation_id)
        data["is_pinned"] = is_pinned
        return api_success(
            data=data,
            message="Chat pinned." if is_pinned else "Chat unpinned.",
        )


class CreateDirectChatView(APIView):
    @extend_schema(tags=["Chat"], summary="Start direct chat", request=CreateDirectChatSerializer)
    def post(self, request):
        serializer = CreateDirectChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            other_user = User.objects.get(id=serializer.validated_data["user_id"])
        except User.DoesNotExist:
            return api_error(message="User not found.", status_code=status.HTTP_404_NOT_FOUND)
        if other_user.id == request.user.id:
            return api_error(message="Cannot chat with yourself.", status_code=status.HTTP_400_BAD_REQUEST)
        conv = ConversationRepository.get_or_create_direct(request.user, other_user)
        return api_success(
            data=ConversationSerializer(conv, context={"request": request}).data,
            message="Direct chat ready.",
            status_code=status.HTTP_201_CREATED,
        )


class CreateGroupView(APIView):
    @extend_schema(tags=["Chat"], summary="Create group chat", request=CreateGroupSerializer)
    def post(self, request):
        serializer = CreateGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        participant_ids = [
            pid for pid in serializer.validated_data["participant_ids"]
            if pid != request.user.id
        ]
        if not participant_ids:
            return api_error(
                message="Add at least one other participant.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        participants = User.objects.filter(id__in=participant_ids)
        found_ids = set(participants.values_list("id", flat=True))
        missing = [pid for pid in participant_ids if pid not in found_ids]
        if missing:
            return api_error(
                message="One or more participants were not found.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        conv = Conversation.objects.create(
            is_group=True,
            group_name=serializer.validated_data["group_name"],
            created_by=request.user,
        )
        conv.participants.add(request.user, *participants)
        return api_success(
            data=ConversationSerializer(conv, context={"request": request}).data,
            message="Group created successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class UpdateGroupView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(tags=["Chat"], summary="Update group name, avatar, or admins-only messaging (admin only)", request=UpdateGroupSerializer)
    def patch(self, request, conversation_id):
        conv, error = _get_group_conversation(request, conversation_id)
        if error:
            return error
        if not conv.is_group_admin(request.user):
            return api_error(
                message="Only the group admin can update group settings.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        serializer = UpdateGroupSerializer(conv, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return api_success(
            data=ConversationSerializer(conv, context={"request": request}).data,
            message="Group updated successfully.",
        )


class RemoveGroupMemberView(APIView):
    @extend_schema(tags=["Chat"], summary="Remove member from group (admin only)")
    def post(self, request, conversation_id, user_id):
        conv, error = _get_group_conversation(request, conversation_id)
        if error:
            return error
        if not conv.is_group_admin(request.user):
            return api_error(
                message="Only the group admin can remove members.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        if user_id == request.user.id:
            return api_error(
                message="Admin cannot remove themselves from the group.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            member = conv.participants.get(id=user_id)
        except User.DoesNotExist:
            return api_error(message="Member not found in this group.", status_code=status.HTTP_404_NOT_FOUND)

        ConversationRepository.remove_participant(conv, member)
        return api_success(
            data=ConversationSerializer(conv, context={"request": request}).data,
            message="Member removed successfully.",
        )


class MessageListView(APIView):
    @extend_schema(
        tags=["Chat"],
        summary="Get messages",
        parameters=[
            OpenApiParameter(
                name="before",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name="around",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Center the page on this message id (search jump).",
            ),
        ],
    )
    def get(self, request, conversation_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return api_error(message="Conversation not found.", status_code=status.HTTP_404_NOT_FOUND)
        if not ConversationRepository.user_in_conversation(conv, request.user):
            return api_error(message="Access denied.", status_code=status.HTTP_403_FORBIDDEN)

        around_id = request.query_params.get("around")
        if around_id:
            try:
                around_id = int(around_id)
            except (TypeError, ValueError):
                around_id = None
        if around_id:
            messages = MessageRepository.get_messages_around(
                conv, user=request.user, around_id=around_id, limit=50
            )
        else:
            before_id = request.query_params.get("before")
            before_id = int(before_id) if before_id else None
            messages = MessageRepository.get_conversation_messages(
                conv,
                user=request.user,
                limit=50,
                before_id=before_id,
            )
            messages = list(reversed(messages))
        MessageRepository.mark_as_read(conv, request.user)
        return api_success(
            data=MessageSerializer(messages, many=True, context={"request": request}).data,
            message="Messages fetched successfully.",
        )


class SendMessageView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(tags=["Chat"], summary="Send message", request=SendMessageSerializer)
    def post(self, request, conversation_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return api_error(message="Conversation not found.", status_code=status.HTTP_404_NOT_FOUND)
        if not ConversationRepository.user_in_conversation(conv, request.user):
            return api_error(message="Access denied.", status_code=status.HTTP_403_FORBIDDEN)
        if ConversationRepository.is_blocked_by(conv, request.user):
            return api_error(
                message="You blocked this chat. Unblock to send messages.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        try:
            MentionService.assert_can_post(conv, request.user)
        except PermissionError as exc:
            return api_error(message=str(exc), status_code=status.HTTP_403_FORBIDDEN)

        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            reply_to = MessageService.resolve_reply_target(conv, data.get("reply_to_id"))
        except ValueError as exc:
            return api_error(message=str(exc), status_code=status.HTTP_400_BAD_REQUEST)

        message_type = data.get("message_type", Message.MessageType.TEXT)
        file = data.get("file")
        if file and message_type == Message.MessageType.TEXT:
            message_type = MessageRepository.detect_message_type(file.name)

        message = MessageRepository.create_message(
            conversation=conv,
            sender=request.user,
            content=data.get("content", ""),
            message_type=message_type,
            file=file,
            file_name=file.name if file else "",
            reply_to=reply_to,
        )
        mentioned_users, mention_everyone = MentionService.resolve(
            conv,
            request.user,
            mentioned_user_ids=MentionService.parse_id_list(data.get("mentioned_user_ids")),
            mention_everyone=bool(data.get("mention_everyone")),
            content=data.get("content", ""),
        )
        if mentioned_users or mention_everyone:
            message = MentionService.attach(message, mentioned_users, mention_everyone)
        # The draft that produced this message is no longer needed.
        MessageService.clear_draft_after_send(conv, request.user)
        broadcast_new_message(message, request)
        return api_success(
            data=MessageSerializer(message, context={"request": request}).data,
            message="Message sent successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class ForwardMessageView(APIView):
    @extend_schema(
        tags=["Chat"],
        summary="Forward a message to other chats",
        description=(
            "Copies the message into each target conversation (max 10). "
            "Copies are flagged `is_forwarded` and keep `forwarded_from` pointing at "
            "the original message. Returns the created messages plus per-target failures."
        ),
        request=ForwardMessageSerializer,
        responses={201: MessageSerializer(many=True)},
    )
    def post(self, request, conversation_id, message_id):
        conv, error = _get_user_conversation(request, conversation_id)
        if error:
            return error

        message = MessageRepository.get_quotable_message(conv, message_id)
        if message is None:
            return api_error(
                message="Message not found or deleted.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = ForwardMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        created, failures = MessageService.forward_message(
            message,
            request.user,
            serializer.validated_data["conversation_ids"],
        )
        for copy in created:
            broadcast_new_message(copy, request)

        if not created:
            return api_error(
                message=failures[0]["error"] if failures else "Nothing was forwarded.",
                data={"failed": failures},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return api_success(
            data={
                "forwarded": MessageSerializer(created, many=True, context={"request": request}).data,
                "failed": failures,
            },
            message=f"Message forwarded to {len(created)} chat(s).",
            status_code=status.HTTP_201_CREATED,
        )


class MessageDraftView(APIView):
    @extend_schema(
        tags=["Chat"],
        summary="Get unsent draft for a chat",
        responses={200: MessageDraftSerializer},
    )
    def get(self, request, conversation_id):
        conv, error = _get_user_conversation(request, conversation_id)
        if error:
            return error
        draft = DraftRepository.get(conv, request.user)
        return api_success(
            data=MessageDraftSerializer(draft, context={"request": request}).data if draft else None,
            message="Draft fetched successfully.",
        )

    @extend_schema(
        tags=["Chat"],
        summary="Save or clear unsent draft",
        description="Blank `content` clears the draft. Pass `reply_to_id` to keep a quoted message with it.",
        request=SaveDraftSerializer,
        responses={200: MessageDraftSerializer},
    )
    def put(self, request, conversation_id):
        conv, error = _get_user_conversation(request, conversation_id)
        if error:
            return error

        serializer = SaveDraftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content = serializer.validated_data["content"]

        if not content.strip():
            DraftRepository.clear(conv, request.user)
            return api_success(data=None, message="Draft cleared.")

        try:
            reply_to = MessageService.resolve_reply_target(
                conv, serializer.validated_data.get("reply_to_id")
            )
        except ValueError as exc:
            return api_error(message=str(exc), status_code=status.HTTP_400_BAD_REQUEST)

        draft = DraftRepository.save(conv, request.user, content=content, reply_to=reply_to)
        return api_success(
            data=MessageDraftSerializer(draft, context={"request": request}).data,
            message="Draft saved.",
        )

    @extend_schema(tags=["Chat"], summary="Delete unsent draft")
    def delete(self, request, conversation_id):
        conv, error = _get_user_conversation(request, conversation_id)
        if error:
            return error
        DraftRepository.clear(conv, request.user)
        return api_success(data=None, message="Draft cleared.")


class DeleteMessageView(APIView):
    @extend_schema(
        tags=["Chat"],
        summary="Delete message for me or for everyone",
        description=(
            "Use `delete_for=me` to hide the message only for the current user "
            "(others still see it). Use `delete_for=everyone` to soft-delete for all "
            "(sender or group admin only). Accepts JSON body or query param."
        ),
        request=DeleteMessageSerializer,
        responses={200: MessageSerializer},
    )
    def delete(self, request, conversation_id, message_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return api_error(message="Conversation not found.", status_code=status.HTTP_404_NOT_FOUND)
        if not ConversationRepository.user_in_conversation(conv, request.user):
            return api_error(message="Access denied.", status_code=status.HTTP_403_FORBIDDEN)

        try:
            message = Message.objects.select_related("sender", "conversation").get(
                id=message_id,
                conversation=conv,
            )
        except Message.DoesNotExist:
            return api_error(message="Message not found.", status_code=status.HTTP_404_NOT_FOUND)

        delete_for = request.data.get("delete_for") or request.query_params.get("delete_for") or "everyone"
        serializer = DeleteMessageSerializer(data={"delete_for": delete_for})
        serializer.is_valid(raise_exception=True)
        delete_for = serializer.validated_data["delete_for"]

        if delete_for == "me":
            MessageRepository.hide_message_for_user(message, request.user)
            return api_success(
                data={
                    "id": message.id,
                    "conversation": conversation_id,
                    "delete_for": "me",
                    "hidden": True,
                },
                message="Message deleted for you.",
            )

        if message.is_deleted:
            return api_success(
                data=MessageSerializer(message, context={"request": request}).data,
                message="Message already deleted.",
            )

        is_sender = message.sender_id == request.user.id
        is_admin = conv.is_group and conv.is_group_admin(request.user)
        if not is_sender and not is_admin:
            return api_error(
                message="Only the sender or group admin can delete for everyone.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        message = MessageRepository.soft_delete_message(message, request.user)
        broadcast_message_deleted(message, request)
        data = MessageSerializer(message, context={"request": request}).data
        data["delete_for"] = "everyone"
        return api_success(
            data=data,
            message="Message deleted for everyone.",
        )


class ReactToMessageView(APIView):
    @extend_schema(tags=["Chat"], summary="Add or toggle emoji reaction on a message", request=ReactToMessageSerializer)
    def post(self, request, conversation_id, message_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return api_error(message="Conversation not found.", status_code=status.HTTP_404_NOT_FOUND)
        if not ConversationRepository.user_in_conversation(conv, request.user):
            return api_error(message="Access denied.", status_code=status.HTTP_403_FORBIDDEN)

        try:
            message = Message.objects.select_related("sender", "conversation").get(
                id=message_id,
                conversation=conv,
            )
        except Message.DoesNotExist:
            return api_error(message="Message not found.", status_code=status.HTTP_404_NOT_FOUND)

        if message.is_deleted:
            return api_error(
                message="Cannot react to a deleted message.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ReactToMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = MessageRepository.toggle_reaction(
            message,
            request.user,
            serializer.validated_data["emoji"],
        )
        broadcast_message_updated(message, request)
        return api_success(
            data=MessageSerializer(message, context={"request": request}).data,
            message="Reaction updated.",
        )


class EditMessageView(APIView):
    @extend_schema(
        tags=["Chat"],
        summary="Edit a text message within the time window",
        description=(
            "Only the sender can edit, and only text messages within "
            "`MESSAGE_EDIT_WINDOW_MINUTES` (default 15) of `created_at`. "
            "Broadcasts `message_updated` over WebSocket."
        ),
        request=EditMessageSerializer,
        responses={200: MessageSerializer},
    )
    def patch(self, request, conversation_id, message_id):
        conv, error = _get_user_conversation(request, conversation_id)
        if error:
            return error

        try:
            message = Message.objects.select_related("sender", "reply_to", "reply_to__sender").get(
                id=message_id,
                conversation=conv,
            )
        except Message.DoesNotExist:
            return api_error(message="Message not found.", status_code=status.HTTP_404_NOT_FOUND)

        serializer = EditMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            message = MessageService.edit_message(
                message,
                request.user,
                serializer.validated_data["content"],
                is_blocked=ConversationRepository.is_blocked_by(conv, request.user),
            )
        except PermissionError as exc:
            return api_error(message=str(exc), status_code=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return api_error(message=str(exc), status_code=status.HTTP_400_BAD_REQUEST)

        broadcast_message_updated(message, request)
        return api_success(
            data=MessageSerializer(message, context={"request": request}).data,
            message="Message edited.",
        )


class MarkReadView(APIView):
    @extend_schema(tags=["Chat"], summary="Mark conversation as read")
    def post(self, request, conversation_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return api_error(message="Conversation not found.", status_code=status.HTTP_404_NOT_FOUND)
        if not ConversationRepository.user_in_conversation(conv, request.user):
            return api_error(message="Access denied.", status_code=status.HTTP_403_FORBIDDEN)
        MessageRepository.mark_as_read(conv, request.user)
        return api_success(message="Marked as read.", data=None)


def _parse_search_params(request):
    query = MessageSearchService.normalize_query(request.query_params.get("q"))
    before_raw = request.query_params.get("before")
    try:
        before_id = int(before_raw) if before_raw else None
    except (TypeError, ValueError):
        before_id = None
    try:
        limit = int(request.query_params.get("limit") or DEFAULT_LIMIT)
    except (TypeError, ValueError):
        limit = DEFAULT_LIMIT
    limit = max(1, min(limit, MAX_LIMIT))
    return query, before_id, limit


class InChatMessageSearchView(APIView):
    @extend_schema(
        tags=["Chat"],
        summary="Search messages in a conversation",
        parameters=[
            OpenApiParameter(name="q", type=str, location=OpenApiParameter.QUERY, required=True),
            OpenApiParameter(name="before", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: MessageSearchHitSerializer(many=True)},
    )
    def get(self, request, conversation_id):
        conv, error = _get_user_conversation(request, conversation_id)
        if error:
            return error
        query, before_id, limit = _parse_search_params(request)
        if len(query) < MIN_QUERY_LENGTH:
            return api_success(
                data={"query": query, "results": [], "has_more": False},
                message="Search query too short.",
            )
        hits = MessageSearchService.search(
            request.user, query, conversation=conv, before_id=before_id, limit=limit
        )
        return api_success(
            data={
                "query": query,
                "results": MessageSearchHitSerializer(
                    hits, many=True, context={"request": request, "query": query}
                ).data,
                "has_more": len(hits) == limit,
            },
            message="Search results fetched.",
        )


class GlobalMessageSearchView(APIView):
    @extend_schema(
        tags=["Chat"],
        summary="Search messages across all conversations",
        parameters=[
            OpenApiParameter(name="q", type=str, location=OpenApiParameter.QUERY, required=True),
            OpenApiParameter(name="before", type=int, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False),
        ],
        responses={200: MessageSearchHitSerializer(many=True)},
    )
    def get(self, request):
        query, before_id, limit = _parse_search_params(request)
        if len(query) < MIN_QUERY_LENGTH:
            return api_success(
                data={"query": query, "results": [], "has_more": False},
                message="Search query too short.",
            )
        hits = MessageSearchService.search(
            request.user, query, before_id=before_id, limit=limit
        )
        return api_success(
            data={
                "query": query,
                "results": MessageSearchHitSerializer(
                    hits, many=True, context={"request": request, "query": query}
                ).data,
                "has_more": len(hits) == limit,
            },
            message="Search results fetched.",
        )
