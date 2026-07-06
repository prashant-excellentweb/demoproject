from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView

from apps.chat.consumers import broadcast_new_message
from apps.chat.models import Conversation, Message
from apps.chat.repositories.conversation_repository import ConversationRepository, MessageRepository
from apps.chat.serializers import (
    ConversationSerializer,
    CreateDirectChatSerializer,
    CreateGroupSerializer,
    MessageSerializer,
    SendMessageSerializer,
    UpdateGroupSerializer,
)
from apps.common.responses import api_error, api_success
from apps.users.models import User


def _get_group_conversation(request, conversation_id):
    try:
        conv = Conversation.objects.get(id=conversation_id, is_group=True)
    except Conversation.DoesNotExist:
        return None, api_error(message="Group not found.", status_code=status.HTTP_404_NOT_FOUND)
    if not ConversationRepository.user_in_conversation(conv, request.user):
        return None, api_error(message="Access denied.", status_code=status.HTTP_403_FORBIDDEN)
    return conv, None


class ConversationListView(APIView):
    @extend_schema(tags=["Chat"], summary="List conversations")
    def get(self, request):
        conversations = ConversationRepository.get_user_conversations(request.user)
        return api_success(
            data=ConversationSerializer(conversations, many=True, context={"request": request}).data,
            message="Conversations fetched successfully.",
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

    @extend_schema(tags=["Chat"], summary="Update group name or avatar (admin only)", request=UpdateGroupSerializer)
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
        ],
    )
    def get(self, request, conversation_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return api_error(message="Conversation not found.", status_code=status.HTTP_404_NOT_FOUND)
        if not ConversationRepository.user_in_conversation(conv, request.user):
            return api_error(message="Access denied.", status_code=status.HTTP_403_FORBIDDEN)

        before_id = request.query_params.get("before")
        before_id = int(before_id) if before_id else None
        messages = MessageRepository.get_conversation_messages(conv, limit=50, before_id=before_id)
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

        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

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
        )
        broadcast_new_message(message, request)
        return api_success(
            data=MessageSerializer(message, context={"request": request}).data,
            message="Message sent successfully.",
            status_code=status.HTTP_201_CREATED,
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
