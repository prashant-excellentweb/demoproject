from collections import defaultdict

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.stories.models import Status
from apps.stories.repositories.status_repository import StatusRepository
from apps.stories.serializers import (
    CreateStatusSerializer,
    StatusFeedResponseSerializer,
    StatusSerializer,
)
from apps.users.serializers import DetailResponseSerializer, UserPublicSerializer


class StatusFeedView(APIView):
    @extend_schema(
        tags=["Stories"],
        summary="Status feed",
        description="My statuses plus contacts' statuses grouped by user (WhatsApp-style stories bar).",
        responses={200: StatusFeedResponseSerializer},
    )
    def get(self, request):
        my_statuses = StatusRepository.get_my_statuses(request.user)
        contact_statuses = StatusRepository.get_contacts_statuses(request.user)

        grouped = defaultdict(list)
        for s in contact_statuses:
            grouped[s.user_id].append(s)

        groups = []
        for user_id, statuses in grouped.items():
            user = statuses[0].user
            has_unviewed = any(
                not getattr(s, "user_views", []) or len(s.user_views) == 0 for s in statuses
            )
            groups.append(
                {
                    "user": UserPublicSerializer(user, context={"request": request}).data,
                    "statuses": StatusSerializer(statuses, many=True, context={"request": request}).data,
                    "has_unviewed": has_unviewed,
                    "latest_at": statuses[0].created_at,
                }
            )
        groups.sort(key=lambda g: g["latest_at"], reverse=True)

        return Response(
            {
                "my_statuses": StatusSerializer(
                    my_statuses, many=True, context={"request": request}
                ).data,
                "contacts": groups,
            }
        )


class CreateStatusView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=["Stories"],
        summary="Create status",
        description=(
            "Post a 24-hour status. Use multipart/form-data.\n\n"
            "**status_type:** text | image | video\n\n"
            "Text: `content` + optional `background_color`. Image/video: `media` file."
        ),
        request=CreateStatusSerializer,
        responses={201: StatusSerializer},
    )
    def post(self, request):
        serializer = CreateStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        status_obj = Status.objects.create(
            user=request.user,
            status_type=data["status_type"],
            content=data.get("content", ""),
            media=data.get("media"),
            background_color=data.get("background_color", "#075E54"),
            expires_at=timezone.now() + timezone.timedelta(hours=settings.STORY_EXPIRY_HOURS),
        )
        return Response(
            StatusSerializer(status_obj, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ViewStatusView(APIView):
    @extend_schema(
        tags=["Stories"],
        summary="Mark status as viewed",
        responses={200: DetailResponseSerializer, 400: DetailResponseSerializer, 404: DetailResponseSerializer},
    )
    def post(self, request, status_id):
        try:
            status_obj = Status.objects.get(id=status_id, expires_at__gt=timezone.now())
        except Status.DoesNotExist:
            return Response({"detail": "Status not found or expired."}, status=status.HTTP_404_NOT_FOUND)
        if status_obj.user_id == request.user.id:
            return Response({"detail": "Cannot view own status."}, status=status.HTTP_400_BAD_REQUEST)
        StatusRepository.mark_viewed(status_obj, request.user)
        return Response({"detail": "Marked as viewed."})


class DeleteStatusView(APIView):
    @extend_schema(
        tags=["Stories"],
        summary="Delete own status",
        responses={204: None, 404: DetailResponseSerializer},
    )
    def delete(self, request, status_id):
        try:
            status_obj = Status.objects.get(id=status_id, user=request.user)
        except Status.DoesNotExist:
            return Response({"detail": "Status not found."}, status=status.HTTP_404_NOT_FOUND)
        status_obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StatusViewersView(APIView):
    @extend_schema(
        tags=["Stories"],
        summary="List status viewers",
        description="Only the status owner can see who viewed their status.",
        responses={200: UserPublicSerializer(many=True), 404: DetailResponseSerializer},
    )
    def get(self, request, status_id):
        try:
            status_obj = Status.objects.get(id=status_id, user=request.user)
        except Status.DoesNotExist:
            return Response({"detail": "Status not found."}, status=status.HTTP_404_NOT_FOUND)
        viewers = [v.viewer for v in status_obj.views.select_related("viewer").all()]
        return Response(UserPublicSerializer(viewers, many=True, context={"request": request}).data)
