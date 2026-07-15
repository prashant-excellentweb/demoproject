from django.urls import path

from apps.chat.views import (
    ArchiveConversationView,
    BlockConversationView,
    ConversationListView,
    CreateDirectChatView,
    CreateGroupView,
    DeleteMessageView,
    MarkReadView,
    MessageListView,
    PinConversationView,
    ReactToMessageView,
    RemoveGroupMemberView,
    SendMessageView,
    ToggleFavouriteView,
    UpdateGroupView,
)

urlpatterns = [
    path("conversations/", ConversationListView.as_view(), name="conversation-list"),
    path("conversations/direct/", CreateDirectChatView.as_view(), name="create-direct"),
    path("conversations/group/", CreateGroupView.as_view(), name="create-group"),
    path(
        "conversations/<int:conversation_id>/favourite/",
        ToggleFavouriteView.as_view(),
        name="toggle-favourite",
    ),
    path(
        "conversations/<int:conversation_id>/archive/",
        ArchiveConversationView.as_view(),
        name="archive-conversation",
    ),
    path(
        "conversations/<int:conversation_id>/block/",
        BlockConversationView.as_view(),
        name="block-conversation",
    ),
    path(
        "conversations/<int:conversation_id>/pin/",
        PinConversationView.as_view(),
        name="pin-conversation",
    ),
    path("conversations/<int:conversation_id>/group/", UpdateGroupView.as_view(), name="update-group"),
    path(
        "conversations/<int:conversation_id>/members/<int:user_id>/remove/",
        RemoveGroupMemberView.as_view(),
        name="remove-group-member",
    ),
    path("conversations/<int:conversation_id>/messages/", MessageListView.as_view(), name="message-list"),
    path(
        "conversations/<int:conversation_id>/messages/<int:message_id>/",
        DeleteMessageView.as_view(),
        name="delete-message",
    ),
    path(
        "conversations/<int:conversation_id>/messages/<int:message_id>/react/",
        ReactToMessageView.as_view(),
        name="react-to-message",
    ),
    path("conversations/<int:conversation_id>/send/", SendMessageView.as_view(), name="send-message"),
    path("conversations/<int:conversation_id>/read/", MarkReadView.as_view(), name="mark-read"),
]
