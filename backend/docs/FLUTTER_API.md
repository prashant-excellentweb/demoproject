# ChatApp API — Flutter Integration Guide

> **Chat + WebSocket implementation (screens, flows, Dio + `web_socket_channel`):**  
> see **[`FLUTTER_CHAT.md`](./FLUTTER_CHAT.md)** — conversation APIs, when to use REST vs WebSocket, and copy-paste Flutter patterns.

## Standard response (every API)

```json
{
  "success": true,
  "message": "Success message",
  "data": { }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | `true` = OK, `false` = error |
| `message` | string | Human-readable status |
| `data` | object/array/null | Actual payload |

**Error example:**
```json
{
  "success": false,
  "message": "Invalid or expired OTP.",
  "data": null
}
```

**Validation error:**
```json
{
  "success": false,
  "message": "Validation failed",
  "data": { "phone_number": ["Enter a valid phone number."] }
}
```

Always read `success` first, then `message`, then `data`.

---

## Swagger / OpenAPI

| Resource | URL |
|----------|-----|
| **Swagger UI** | http://localhost:9000/api/docs/ |
| **ReDoc** | http://localhost:9000/api/redoc/ |
| **OpenAPI JSON** | http://localhost:9000/api/schema/ |
| **OpenAPI YAML file** | `backend/docs/openapi.yaml` |

In Swagger UI, click **Authorize** and enter: `Bearer <your_access_token>`

---

## Base URL

```
http://<server-ip>:9000/api
```

For Android emulator use `http://10.0.2.2:9000/api`  
For iOS simulator use `http://127.0.0.1:9000/api`

---

## Authentication

All endpoints except `send-otp` and `verify-otp` require:

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

### 1. Send OTP
```http
POST /auth/send-otp/
```
```json
{ "phone_number": "+1234567890" }
```

### 2. Verify OTP
```http
POST /auth/verify-otp/
```
```json
{ "phone_number": "+1234567890", "otp_code": "123456" }
```
**Response:**
```json
{
  "success": true,
  "message": "Login successful.",
  "data": {
    "access": "eyJ...",
    "refresh": "eyJ...",
    "user": { "id": 1, "phone_number": "+1234567890", "display_name": "", ... },
    "is_new_user": true
  }
}
```

### 3. Refresh token
```http
POST /auth/token/refresh/
```
```json
{ "refresh": "eyJ..." }
```

### 4. Logout
```http
POST /auth/logout/
```

---

## Auth & Profile APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/profile/` | Get current user profile |
| PATCH | `/auth/profile/` | Update name, about, avatar (multipart) |
| DELETE | `/auth/profile/` | Soft-delete account (frees phone number) |
| GET | `/auth/search/?q=john` | Search users (min 2 chars) |
| GET | `/auth/users/{id}/` | Get user by ID |
| POST | `/auth/users/{id}/report/` | Report user `{ "reason", "details?", "conversation_id?" }` |

---

## Chat APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/chat/conversations/` | List all conversations |
| GET | `/chat/conversations/?filter=unread` | Filter: `all` \| `unread` \| `groups` \| `favourites` \| `archived` \| `blocked` |
| POST | `/chat/conversations/{id}/favourite/` | Toggle favourite (per user) |
| POST | `/chat/conversations/{id}/archive/` | Archive/unarchive `{ "action": "archive" \| "unarchive" }` |
| POST | `/chat/conversations/{id}/block/` | Block/unblock `{ "action": "block" \| "unblock" }` |
| POST | `/chat/conversations/{id}/pin/` | Pin/unpin `{ "action": "pin" \| "unpin" }` |
| POST | `/chat/conversations/direct/` | Start 1:1 chat `{ "user_id": 2 }` |
| POST | `/chat/conversations/group/` | Create group `{ "group_name": "Family", "participant_ids": [2,3] }` |
| PATCH | `/chat/conversations/{id}/group/` | Update group name/avatar (admin only, multipart) |
| POST | `/chat/conversations/{id}/members/{user_id}/remove/` | Remove member (admin only) |
| GET | `/chat/conversations/{id}/messages/?before=100` | Get messages (paginated; excludes your "delete for me") |
| POST | `/chat/conversations/{id}/send/` | Send message (multipart) |
| DELETE | `/chat/conversations/{id}/messages/{message_id}/` | Delete for me **or** everyone |
| POST | `/chat/conversations/{id}/messages/{message_id}/react/` | Add/toggle emoji reaction |
| POST | `/chat/conversations/{id}/read/` | Mark as read |

### Chat list filters & favourites

```http
GET /chat/conversations/?filter=all
GET /chat/conversations/?filter=unread
GET /chat/conversations/?filter=groups
GET /chat/conversations/?filter=favourites
GET /chat/conversations/?filter=archived
GET /chat/conversations/?filter=blocked
```

| `filter` | Meaning |
|----------|---------|
| `all` | Main inbox (excludes archived; pinned then favourites sorted to top) |
| `unread` | Unread chats in inbox |
| `groups` | Group chats in inbox |
| `favourites` | Favourite chats in inbox |
| `archived` | Archived chats only |
| `blocked` | Chats you blocked |

Each conversation includes `is_favourite`, `is_archived`, `is_blocked`, `is_pinned`.

```http
POST /chat/conversations/1/favourite/
```

```http
POST /chat/conversations/1/archive/
{ "action": "archive" }
```

```http
POST /chat/conversations/1/archive/
{ "action": "unarchive" }
```

```http
POST /chat/conversations/1/block/
{ "action": "block" }
```

```http
POST /chat/conversations/1/block/
{ "action": "unblock" }
```

```http
POST /chat/conversations/1/pin/
{ "action": "pin" }
```

```http
POST /chat/conversations/1/pin/
{ "action": "unpin" }
```

**Notes**
- Archive is per-user. New messages unarchive the chat for participants again.
- Block is per-user. Blocked users cannot **send** in that chat until they unblock.
- Pin is per-user. Pinned chats sort above favourites in the inbox.
- Sending to a blocked chat returns `403` with message to unblock first.

### Report user

```http
POST /auth/users/2/report/
```
```json
{
  "reason": "spam",
  "details": "Sending ads",
  "conversation_id": 1
}
```

`reason`: `spam` | `harassment` | `inappropriate` | `fake` | `other`

### Delete account

```http
DELETE /auth/profile/
```

Soft-deletes the account (`is_active=false`), renames the phone so it can be reused, and clears the avatar.

```dart
await dio.post('/chat/conversations/$convId/archive/', data: {'action': 'archive'});
await dio.post('/chat/conversations/$convId/block/', data: {'action': 'block'});
await dio.post('/chat/conversations/$convId/pin/', data: {'action': 'pin'});
await dio.post('/auth/users/$userId/report/', data: {'reason': 'spam'});
await dio.delete('/auth/profile/');
```

### Send text message
```http
POST /chat/conversations/1/send/
Content-Type: multipart/form-data

content=Hello
message_type=text
```

### Send image / video / PDF
```http
POST /chat/conversations/1/send/
Content-Type: multipart/form-data

file=<binary>
message_type=image   // image | video | pdf | document | audio
```

**message_type values:** `text`, `image`, `video`, `pdf`, `document`, `audio`

### Delete message — for me vs everyone

```http
DELETE /chat/conversations/1/messages/42/
Content-Type: application/json
Authorization: Bearer <access_token>

{ "delete_for": "me" }
```

| `delete_for` | Who can use it | Effect |
|--------------|----------------|--------|
| `me` | Any participant | Message hidden **only for you**. Others still see it. Removed from your message list / chat preview. |
| `everyone` | Sender, or group admin | Soft-delete for **all**. Content cleared; everyone sees `"This message was deleted"`. Real-time WS event `message_deleted`. |

**Delete for me — success response:**
```json
{
  "success": true,
  "message": "Message deleted for you.",
  "data": {
    "id": 42,
    "conversation": 1,
    "delete_for": "me",
    "hidden": true
  }
}
```

**Delete for everyone — success response:**
```json
{
  "success": true,
  "message": "Message deleted for everyone.",
  "data": {
    "id": 42,
    "conversation": 1,
    "is_deleted": true,
    "content": "",
    "delete_for": "everyone",
    "reactions": [],
    "...": "..."
  }
}
```

**Flutter (Dio):**
```dart
// Delete for me only
await dio.delete(
  '/chat/conversations/$convId/messages/$messageId/',
  data: {'delete_for': 'me'},
);

// Delete for everyone
await dio.delete(
  '/chat/conversations/$convId/messages/$messageId/',
  data: {'delete_for': 'everyone'},
);
```

### React to a message

```http
POST /chat/conversations/1/messages/42/react/
Content-Type: application/json

{ "emoji": "👍" }
```

**Allowed emojis:** `👍` `❤️` `😂` `😮` `😢` `🙏` `🔥` `👏`

- Same emoji again → removes your reaction (toggle)
- Different emoji → replaces your previous reaction
- One reaction per user per message

**Response `data` includes:**
```json
{
  "id": 42,
  "reactions": [
    { "emoji": "👍", "count": 2, "user_ids": [1, 3] }
  ],
  "my_reaction": "👍"
}
```

Real-time: WebSocket event `message_updated` with the full message object.

### Group admin

Group creator is admin (`created_by` / `is_admin: true` on conversation).

```http
PATCH /chat/conversations/1/group/
Content-Type: multipart/form-data

group_name=Family Chat
group_avatar=<optional file>
```

```http
POST /chat/conversations/1/members/5/remove/
```

---

## Stories / Status APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stories/feed/` | My + contacts' statuses |
| POST | `/stories/create/` | Create status (multipart) |
| POST | `/stories/{id}/view/` | Mark status viewed |
| DELETE | `/stories/{id}/delete/` | Delete own status |
| GET | `/stories/{id}/viewers/` | Who viewed (owner only) |

### Create text status
```
POST /stories/create/
status_type=text
content=Hello world
background_color=#075E54
```

### Create image status
```
POST /stories/create/
status_type=image
media=<file>
```

---

## WebSocket (real-time)

```
ws://<host>:9000/ws/chat/?token=<access_token>
```

### Send (client → server)
```json
{ "action": "join_conversation", "conversation_id": 1 }
{ "action": "leave_conversation" }
{ "action": "typing", "is_typing": true }
{ "action": "mark_read", "conversation_id": 1 }
```

### Receive (server → client)
```json
{ "type": "message", "message": { "id": 1, "content": "Hi", "sender": {...}, "reactions": [], "my_reaction": null } }
{ "type": "message_deleted", "message": { "id": 1, "is_deleted": true, "content": "" } }
{ "type": "message_updated", "message": { "id": 1, "reactions": [...], "my_reaction": "❤️" } }
{ "type": "typing", "user_id": 2, "user_name": "John", "is_typing": true }
```

| Event | When |
|-------|------|
| `message` | New message sent |
| `message_deleted` | Delete for everyone |
| `message_updated` | Reaction added/changed/removed |
| `typing` | Someone is typing |

**Note:** "Delete for me" does **not** broadcast — only your client should remove the message locally after the API succeeds.

**Flutter packages:** `web_socket_channel`, `dio` or `http`, `flutter_secure_storage` for tokens.

---

## Flutter code snippet (Dio)

```dart
final dio = Dio(BaseOptions(
  baseUrl: 'http://10.0.2.2:9000/api',
  headers: {'Authorization': 'Bearer $accessToken'},
));

// Send OTP
await dio.post('/auth/send-otp/', data: {'phone_number': '+1234567890'});

// Verify OTP — read from data
final res = await dio.post('/auth/verify-otp/', data: {
  'phone_number': '+1234567890',
  'otp_code': '111111',
});
if (res.data['success'] == true) {
  final accessToken = res.data['data']['access'];
}

// List conversations
final chats = await dio.get('/chat/conversations/');

// Send image
final form = FormData.fromMap({
  'file': await MultipartFile.fromFile(path),
  'message_type': 'image',
});
await dio.post('/chat/conversations/1/send/', data: form);

// React
await dio.post('/chat/conversations/1/messages/42/react/', data: {'emoji': '❤️'});

// Delete for me
await dio.delete('/chat/conversations/1/messages/42/', data: {'delete_for': 'me'});

// Delete for everyone
await dio.delete('/chat/conversations/1/messages/42/', data: {'delete_for': 'everyone'});
```

---

## Generate OpenAPI file (for codegen)

```bash
cd backend
pip install drf-spectacular
python manage.py spectacular --file docs/openapi.yaml --format openapi
```

Use with **openapi_generator** for Dart client:
```bash
openapi-generator generate -i openapi.yaml -g dart-dio -o ./chatapp_api
```

**Live Swagger UI:** http://localhost:9000/api/docs/  
Authorize with: `Bearer <access_token>`
