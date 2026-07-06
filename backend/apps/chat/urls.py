from django.urls import path

from apps.chat.views import (
    ConversationListView,
    CreateDirectChatView,
    CreateGroupView,
    MarkReadView,
    MessageListView,
    RemoveGroupMemberView,
    SendMessageView,
    UpdateGroupView,
)

urlpatterns = [
    path("conversations/", ConversationListView.as_view(), name="conversation-list"),
    path("conversations/direct/", CreateDirectChatView.as_view(), name="create-direct"),
    path("conversations/group/", CreateGroupView.as_view(), name="create-group"),
    path("conversations/<int:conversation_id>/group/", UpdateGroupView.as_view(), name="update-group"),
    path(
        "conversations/<int:conversation_id>/members/<int:user_id>/remove/",
        RemoveGroupMemberView.as_view(),
        name="remove-group-member",
    ),
    path("conversations/<int:conversation_id>/messages/", MessageListView.as_view(), name="message-list"),
    path("conversations/<int:conversation_id>/send/", SendMessageView.as_view(), name="send-message"),
    path("conversations/<int:conversation_id>/read/", MarkReadView.as_view(), name="mark-read"),
]
