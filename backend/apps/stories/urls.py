from django.urls import path

from apps.stories.views import (
    CreateStatusView,
    DeleteStatusView,
    StatusFeedView,
    StatusViewersView,
    ViewStatusView,
)

urlpatterns = [
    path("feed/", StatusFeedView.as_view(), name="status-feed"),
    path("create/", CreateStatusView.as_view(), name="create-status"),
    path("<int:status_id>/view/", ViewStatusView.as_view(), name="view-status"),
    path("<int:status_id>/delete/", DeleteStatusView.as_view(), name="delete-status"),
    path("<int:status_id>/viewers/", StatusViewersView.as_view(), name="status-viewers"),
]
