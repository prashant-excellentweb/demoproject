# Frontend / Mobile API notes

This app’s REST + WebSocket contract is documented for Flutter and web clients here:

- **Flutter guide (payloads, examples):** [`../backend/docs/FLUTTER_API.md`](../backend/docs/FLUTTER_API.md)
- **Flutter privacy (photo / about / last seen / status):** [`../backend/docs/FLUTTER_PRIVACY.md`](../backend/docs/FLUTTER_PRIVACY.md)
- **Flutter reply / forward / draft:** [`../backend/docs/FLUTTER_REPLY_FORWARD_DRAFT.md`](../backend/docs/FLUTTER_REPLY_FORWARD_DRAFT.md)
- **Flutter edit message:** [`../backend/docs/FLUTTER_EDIT_MESSAGE.md`](../backend/docs/FLUTTER_EDIT_MESSAGE.md)
- **Flutter message search:** [`../backend/docs/FLUTTER_MESSAGE_SEARCH.md`](../backend/docs/FLUTTER_MESSAGE_SEARCH.md)
- **Flutter group mentions + admins-only:** [`../backend/docs/FLUTTER_GROUP_MENTIONS_ADMINS.md`](../backend/docs/FLUTTER_GROUP_MENTIONS_ADMINS.md)
- **Flutter chat + WebSocket guide:** [`../backend/docs/FLUTTER_CHAT.md`](../backend/docs/FLUTTER_CHAT.md)
- **Swagger UI:** http://localhost:9000/api/docs/
- **OpenAPI YAML:** [`../backend/docs/openapi.yaml`](../backend/docs/openapi.yaml)

## Chat list filters

Tabs: **All** · **Unread** · **Favourites** · **Groups** · **Archived** · **Blocked**

| Action | API |
|--------|-----|
| List with filter | `GET /chat/conversations/?filter=all\|unread\|groups\|favourites\|archived\|blocked` |
| Toggle favourite | `POST /chat/conversations/{id}/favourite/` |
| Archive / unarchive | `POST /chat/conversations/{id}/archive/` body `{ "action": "archive" \| "unarchive" }` |
| Block / unblock | `POST /chat/conversations/{id}/block/` body `{ "action": "block" \| "unblock" }` |
| Pin / unpin | `POST /chat/conversations/{id}/pin/` body `{ "action": "pin" \| "unpin" }` |
| Report user | `POST /auth/users/{id}/report/` body `{ "reason", "details?", "conversation_id?" }` |
| Delete account | `DELETE /auth/profile/` |

Conversation payload includes `is_favourite`, `is_archived`, `is_blocked`, `is_pinned`, and `draft` (unsent text + optional quote). Archived chats are hidden from the main inbox filters. Pinned chats sort above favourites.

## Reply, forward, draft

| Action | API |
|--------|-----|
| Reply | `POST /chat/conversations/{id}/send/` with `reply_to_id` |
| Forward | `POST /chat/conversations/{id}/messages/{messageId}/forward/` body `{ "conversation_ids": [2, 3] }` (max 10) |
| Get draft | `GET /chat/conversations/{id}/draft/` |
| Save draft | `PUT /chat/conversations/{id}/draft/` body `{ "content", "reply_to_id?" }` |
| Clear draft | `DELETE /chat/conversations/{id}/draft/` (also cleared automatically after send) |

Full Flutter walkthrough: [`FLUTTER_REPLY_FORWARD_DRAFT.md`](../backend/docs/FLUTTER_REPLY_FORWARD_DRAFT.md).

## Message delete (web + Flutter)

| Action | API | UI |
|--------|-----|----|
| Delete for me | `DELETE /chat/conversations/{id}/messages/{messageId}/` body `{ "delete_for": "me" }` | Message removed only from **your** chat |
| Delete for everyone | same URL, body `{ "delete_for": "everyone" }` | Everyone sees “This message was deleted” |

- **Delete for me:** any chat participant  
- **Delete for everyone:** message sender, or group admin  

## Edit message (15-minute window)

`PATCH /chat/conversations/{id}/messages/{messageId}/edit/`  
Body: `{ "content": "updated text" }`  

Sender only, **text** messages, within 15 minutes of send. Payload includes `is_edited` and `edited_at`. Others get WebSocket `message_updated`.

Walkthrough: [`FLUTTER_EDIT_MESSAGE.md`](../backend/docs/FLUTTER_EDIT_MESSAGE.md).

## Message search

| Action | API |
|--------|-----|
| In this chat | `GET /chat/conversations/{id}/messages/search/?q=` |
| All chats | `GET /chat/messages/search/?q=` |
| Jump to hit | `GET /chat/conversations/{id}/messages/?around={messageId}` |

Min query length 2. Inbox search lists matching **chats** locally and matching **messages** from the global API.

Walkthrough: [`FLUTTER_MESSAGE_SEARCH.md`](../backend/docs/FLUTTER_MESSAGE_SEARCH.md).

## Group mentions & admins-only messaging

| Action | API |
|--------|-----|
| Mention members | `POST /chat/conversations/{id}/send/` with `mentioned_user_ids` and/or `mention_everyone` |
| Only admins can send | `PATCH /chat/conversations/{id}/group/` with `admins_only_messages` (admin only) |

Conversation includes `admins_only_messages` and `is_admin`. Messages include `mentions`, `mention_everyone`, `mentioned_me`. Mentions are ignored in 1:1. Non-admins get 403 on send/forward while admins-only is on.

Walkthrough: [`FLUTTER_GROUP_MENTIONS_ADMINS.md`](../backend/docs/FLUTTER_GROUP_MENTIONS_ADMINS.md).

## Reactions

`POST /chat/conversations/{id}/messages/{messageId}/react/`  
Body: `{ "emoji": "👍" }`  
Allowed: 👍 ❤️ 😂 😮 😢 🙏 🔥 👏  

## WebSocket events to handle

| `type` | Meaning |
|--------|---------|
| `message` | New message |
| `message_deleted` | Deleted for everyone |
| `message_updated` | Reaction changed |
| `typing` | Typing indicator |

“Delete for me” has **no** WebSocket event — remove the bubble locally after a successful API call.
