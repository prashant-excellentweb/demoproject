from collections import defaultdict

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from apps.common.responses import api_error, api_success
from apps.stories.models import Status
from apps.stories.repositories.status_repository import StatusRepository
from apps.stories.serializers import CreateStatusSerializer, StatusSerializer
from apps.users.serializers import UserPublicSerializer


class StatusFeedView(APIView):
    @extend_schema(tags=["Stories"], summary="Status feed")
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

        return api_success(
            data={
                "my_statuses": StatusSerializer(
                    my_statuses, many=True, context={"request": request}
                ).data,
                "contacts": groups,
            },
            message="Status feed fetched successfully.",
        )


class CreateStatusView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(tags=["Stories"], summary="Create status", request=CreateStatusSerializer)
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
        return api_success(
            data=StatusSerializer(status_obj, context={"request": request}).data,
            message="Status created successfully.",
            status_code=status.HTTP_201_CREATED,
        )


class ViewStatusView(APIView):
    @extend_schema(tags=["Stories"], summary="Mark status as viewed")
    def post(self, request, status_id):
        try:
            status_obj = Status.objects.get(id=status_id, expires_at__gt=timezone.now())
        except Status.DoesNotExist:
            return api_error(message="Status not found or expired.", status_code=status.HTTP_404_NOT_FOUND)
        if status_obj.user_id == request.user.id:
            return api_error(message="Cannot view own status.", status_code=status.HTTP_400_BAD_REQUEST)
        StatusRepository.mark_viewed(status_obj, request.user)
        return api_success(message="Marked as viewed.", data=None)


class DeleteStatusView(APIView):
    @extend_schema(tags=["Stories"], summary="Delete own status")
    def delete(self, request, status_id):
        try:
            status_obj = Status.objects.get(id=status_id, user=request.user)
        except Status.DoesNotExist:
            return api_error(message="Status not found.", status_code=status.HTTP_404_NOT_FOUND)
        status_obj.delete()
        return api_success(message="Status deleted successfully.", data=None)


class StatusViewersView(APIView):
    @extend_schema(tags=["Stories"], summary="List status viewers")
    def get(self, request, status_id):
        try:
            status_obj = Status.objects.get(id=status_id, user=request.user)
        except Status.DoesNotExist:
            return api_error(message="Status not found.", status_code=status.HTTP_404_NOT_FOUND)
        viewers = [v.viewer for v in status_obj.views.select_related("viewer").all()]
        return api_success(
            data=UserPublicSerializer(viewers, many=True, context={"request": request}).data,
            message="Status viewers fetched successfully.",
        )
