from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
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
)
from apps.users.models import User
from apps.users.serializers import DetailResponseSerializer


class ConversationListView(APIView):
    @extend_schema(
        tags=["Chat"],
        summary="List conversations",
        description="All conversations for the current user with last message and unread count.",
        responses={200: ConversationSerializer(many=True)},
    )
    def get(self, request):
        conversations = ConversationRepository.get_user_conversations(request.user)
        return Response(
            ConversationSerializer(conversations, many=True, context={"request": request}).data
        )


class CreateDirectChatView(APIView):
    @extend_schema(
        tags=["Chat"],
        summary="Start direct chat",
        description="Create or return existing 1:1 conversation with another user.",
        request=CreateDirectChatSerializer,
        responses={201: ConversationSerializer, 400: DetailResponseSerializer, 404: DetailResponseSerializer},
    )
    def post(self, request):
        serializer = CreateDirectChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            other_user = User.objects.get(id=serializer.validated_data["user_id"])
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if other_user.id == request.user.id:
            return Response({"detail": "Cannot chat with yourself."}, status=status.HTTP_400_BAD_REQUEST)
        conv = ConversationRepository.get_or_create_direct(request.user, other_user)
        return Response(
            ConversationSerializer(conv, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CreateGroupView(APIView):
    @extend_schema(
        tags=["Chat"],
        summary="Create group chat",
        request=CreateGroupSerializer,
        responses={201: ConversationSerializer},
    )
    def post(self, request):
        serializer = CreateGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        participant_ids = serializer.validated_data["participant_ids"]
        participants = User.objects.filter(id__in=participant_ids)
        conv = Conversation.objects.create(
            is_group=True,
            group_name=serializer.validated_data["group_name"],
        )
        conv.participants.add(request.user, *participants)
        return Response(
            ConversationSerializer(conv, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class MessageListView(APIView):
    @extend_schema(
        tags=["Chat"],
        summary="Get messages",
        description="Paginated messages for a conversation (latest 50). Marks messages as read.",
        parameters=[
            OpenApiParameter(
                name="before",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Message ID — load messages older than this (infinite scroll)",
            ),
        ],
        responses={200: MessageSerializer(many=True), 403: DetailResponseSerializer, 404: DetailResponseSerializer},
    )
    def get(self, request, conversation_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        if not ConversationRepository.user_in_conversation(conv, request.user):
            return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

        before_id = request.query_params.get("before")
        before_id = int(before_id) if before_id else None
        messages = MessageRepository.get_conversation_messages(conv, limit=50, before_id=before_id)
        messages = list(reversed(messages))
        MessageRepository.mark_as_read(conv, request.user)
        return Response(MessageSerializer(messages, many=True, context={"request": request}).data)


class SendMessageView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=["Chat"],
        summary="Send message",
        description=(
            "Send text or media message. Use multipart/form-data.\n\n"
            "**message_type:** text | image | video | pdf | document | audio\n\n"
            "For media types, include `file`. For text, include `content`."
        ),
        request=SendMessageSerializer,
        responses={201: MessageSerializer, 403: DetailResponseSerializer, 404: DetailResponseSerializer},
    )
    def post(self, request, conversation_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        if not ConversationRepository.user_in_conversation(conv, request.user):
            return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)

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
        return Response(
            MessageSerializer(message, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class MarkReadView(APIView):
    @extend_schema(
        tags=["Chat"],
        summary="Mark conversation as read",
        responses={200: DetailResponseSerializer, 403: DetailResponseSerializer, 404: DetailResponseSerializer},
    )
    def post(self, request, conversation_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        if not ConversationRepository.user_in_conversation(conv, request.user):
            return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        MessageRepository.mark_as_read(conv, request.user)
        return Response({"detail": "Marked as read."})
