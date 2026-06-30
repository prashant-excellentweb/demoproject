# ChatApp API — Flutter Integration Guide

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
| GET | `/auth/search/?q=john` | Search users (min 2 chars) |
| GET | `/auth/users/{id}/` | Get user by ID |

---

## Chat APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/chat/conversations/` | List all conversations |
| POST | `/chat/conversations/direct/` | Start 1:1 chat `{ "user_id": 2 }` |
| POST | `/chat/conversations/group/` | Create group `{ "group_name": "Family", "participant_ids": [2,3] }` |
| GET | `/chat/conversations/{id}/messages/?before=100` | Get messages (paginated) |
| POST | `/chat/conversations/{id}/send/` | Send message (multipart) |
| POST | `/chat/conversations/{id}/read/` | Mark as read |

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
{ "type": "message", "message": { "id": 1, "content": "Hi", "sender": {...}, ... } }
{ "type": "typing", "user_id": 2, "user_name": "John", "is_typing": true }
```

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
