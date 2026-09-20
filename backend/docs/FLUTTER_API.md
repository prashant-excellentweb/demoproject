# ChatApp API — Flutter Integration Guide

> **Chat + WebSocket implementation (screens, flows, Dio + `web_socket_channel`):**  
> see **[`FLUTTER_CHAT.md`](./FLUTTER_CHAT.md)** — conversation APIs, when to use REST vs WebSocket, and copy-paste Flutter patterns.

> **Privacy (Profile photo / About / Last seen / Status):**  
> see **[`FLUTTER_PRIVACY.md`](./FLUTTER_PRIVACY.md)** — settings API, redaction rules, Flutter models & UI checklist.

> **Reply, Forward & Draft:**  
> see **[`FLUTTER_REPLY_FORWARD_DRAFT.md`](./FLUTTER_REPLY_FORWARD_DRAFT.md)** — `reply_to_id`, forward picker, draft autosave.

> **Edit message (15-minute window):**  
> see **[`FLUTTER_EDIT_MESSAGE.md`](./FLUTTER_EDIT_MESSAGE.md)** — `PATCH …/edit/`, `is_edited`, WebSocket `message_updated`.

> **Message search (in-chat & global):**  
> see **[`FLUTTER_MESSAGE_SEARCH.md`](./FLUTTER_MESSAGE_SEARCH.md)** — `q`, `around`, snippets.

> **Group mentions + admins-only messaging:**  
> see **[`FLUTTER_GROUP_MENTIONS_ADMINS.md`](./FLUTTER_GROUP_MENTIONS_ADMINS.md)** — `@name`, `@everyone`, `admins_only_messages`.

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
| GET | `/auth/profile/` | Get current user profile (includes privacy settings) |
| PATCH | `/auth/profile/` | Update name, about, avatar, **privacy** (multipart or JSON) |
| DELETE | `/auth/profile/` | Soft-delete account (frees phone number) |
| GET | `/auth/search/?q=john` | Search users (min 2 chars; fields redacted by privacy) |
| GET | `/auth/users/{id}/` | Get user by ID (fields redacted by privacy) |
| POST | `/auth/users/{id}/report/` | Report user `{ "reason", "details?", "conversation_id?" }` |

---

## Privacy settings (Profile photo / About / Last seen / Status)

WhatsApp-style visibility controls. The **owner always sees their own data**. Other users receive redacted fields based on these settings.

### Values (same for all four fields)

| Value | Meaning |
|-------|---------|
| `everyone` | Any authenticated ChatApp user |
| `contacts` | Users who share a conversation with you |
| `nobody` | Only you |

### Fields on the user profile

| Field | Controls | Default |
|-------|----------|---------|
| `profile_photo_privacy` | Who sees `avatar_url` | `everyone` |
| `about_privacy` | Who sees `about` | `everyone` |
| `last_seen_privacy` | Who sees `is_online` + `last_seen` | `everyone` |
| `status_privacy` | Who sees your status/stories in the feed | `contacts` |

### Read own privacy (GET profile)

```http
GET /auth/profile/
Authorization: Bearer <access_token>
```

```json
{
  "success": true,
  "message": "Profile fetched successfully.",
  "data": {
    "id": 1,
    "phone_number": "+1234567890",
    "display_name": "Alex",
    "about": "Hey there!",
    "avatar_url": "http://…/media/avatars/…",
    "is_online": true,
    "last_seen": "2026-09-19T10:00:00Z",
    "profile_setup_complete": true,
    "profile_photo_privacy": "everyone",
    "about_privacy": "contacts",
    "last_seen_privacy": "nobody",
    "status_privacy": "contacts"
  }
}
```

### Update privacy (PATCH profile)

JSON:

```http
PATCH /auth/profile/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "profile_photo_privacy": "contacts",
  "about_privacy": "everyone",
  "last_seen_privacy": "nobody",
  "status_privacy": "contacts"
}
```

Or multipart (same as avatar update):

```http
PATCH /auth/profile/
Content-Type: multipart/form-data

profile_photo_privacy=contacts
about_privacy=everyone
last_seen_privacy=nobody
status_privacy=contacts
```

You can combine privacy with name/about/avatar in one request.

### How redaction works for other users

When you call `GET /auth/users/{id}/`, search, conversation participants, or message senders:

| Hidden field | API value when not allowed |
|--------------|----------------------------|
| Profile photo | `avatar_url: null` |
| About | `about: ""` |
| Last seen / online | `last_seen: null`, `is_online: false` |

**Status:** users with `status_privacy: nobody` never appear in `GET /stories/feed/` for others. Viewing a status ID directly returns `403` if privacy blocks it.

**Contacts** = users who share at least one conversation (1:1 or group).

### Flutter model

```dart
enum PrivacyVisibility { everyone, contacts, nobody }

PrivacyVisibility privacyFromString(String? v) {
  switch (v) {
    case 'contacts':
      return PrivacyVisibility.contacts;
    case 'nobody':
      return PrivacyVisibility.nobody;
    default:
      return PrivacyVisibility.everyone;
  }
}

String privacyToString(PrivacyVisibility v) => v.name; // everyone|contacts|nobody

class User {
  final int id;
  final String phoneNumber;
  final String displayName;
  final String about;
  final String? avatarUrl;
  final bool isOnline;
  final DateTime? lastSeen;
  final PrivacyVisibility? profilePhotoPrivacy; // only on own profile
  final PrivacyVisibility? aboutPrivacy;
  final PrivacyVisibility? lastSeenPrivacy;
  final PrivacyVisibility? statusPrivacy;

  User.fromJson(Map<String, dynamic> j)
      : id = j['id'],
        phoneNumber = j['phone_number'] ?? '',
        displayName = j['display_name'] ?? '',
        about = j['about'] ?? '',
        avatarUrl = j['avatar_url'],
        isOnline = j['is_online'] == true,
        lastSeen = j['last_seen'] != null ? DateTime.parse(j['last_seen']) : null,
        profilePhotoPrivacy = j['profile_photo_privacy'] != null
            ? privacyFromString(j['profile_photo_privacy'])
            : null,
        aboutPrivacy = j['about_privacy'] != null
            ? privacyFromString(j['about_privacy'])
            : null,
        lastSeenPrivacy = j['last_seen_privacy'] != null
            ? privacyFromString(j['last_seen_privacy'])
            : null,
        statusPrivacy = j['status_privacy'] != null
            ? privacyFromString(j['status_privacy'])
            : null;
}
```

### Flutter: update privacy with Dio

```dart
Future<User> updatePrivacy({
  required Dio dio,
  PrivacyVisibility? profilePhoto,
  PrivacyVisibility? about,
  PrivacyVisibility? lastSeen,
  PrivacyVisibility? status,
}) async {
  final body = <String, dynamic>{};
  if (profilePhoto != null) body['profile_photo_privacy'] = privacyToString(profilePhoto);
  if (about != null) body['about_privacy'] = privacyToString(about);
  if (lastSeen != null) body['last_seen_privacy'] = privacyToString(lastSeen);
  if (status != null) body['status_privacy'] = privacyToString(status);

  final res = await dio.patch('/auth/profile/', data: body);
  final data = res.data['data'] as Map<String, dynamic>;
  return User.fromJson(data);
}
```

### Flutter UI tips

1. **Own profile / settings screen** — show four pickers (Everyone / My contacts / Nobody); save via `PATCH /auth/profile/`.
2. **Chat header last seen** — if `last_seen == null && !is_online`, hide the subtitle (privacy redacted); do **not** show “offline”.
3. **Avatar** — if `avatar_url == null`, show initials placeholder (may mean no photo **or** privacy).
4. **About on contact info** — empty string may mean privacy; don’t treat as an error.
5. **Status tab** — rely on `/stories/feed/`; users who set Status to Nobody won’t appear. Handle `403` on `/stories/{id}/view/`.

### Example privacy settings screen (Flutter)

```dart
class PrivacySettingsPage extends StatefulWidget {
  const PrivacySettingsPage({super.key, required this.user, required this.onSaved});
  final User user;
  final ValueChanged<User> onSaved;

  @override
  State<PrivacySettingsPage> createState() => _PrivacySettingsPageState();
}

class _PrivacySettingsPageState extends State<PrivacySettingsPage> {
  late PrivacyVisibility photo;
  late PrivacyVisibility about;
  late PrivacyVisibility lastSeen;
  late PrivacyVisibility status;
  bool saving = false;

  @override
  void initState() {
    super.initState();
    photo = widget.user.profilePhotoPrivacy ?? PrivacyVisibility.everyone;
    about = widget.user.aboutPrivacy ?? PrivacyVisibility.everyone;
    lastSeen = widget.user.lastSeenPrivacy ?? PrivacyVisibility.everyone;
    status = widget.user.statusPrivacy ?? PrivacyVisibility.contacts;
  }

  Future<void> _save(Dio dio) async {
    setState(() => saving = true);
    try {
      final updated = await updatePrivacy(
        dio: dio,
        profilePhoto: photo,
        about: about,
        lastSeen: lastSeen,
        status: status,
      );
      widget.onSaved(updated);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Privacy updated')),
      );
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  Widget _row(String title, PrivacyVisibility value, ValueChanged<PrivacyVisibility> onChanged) {
    return ListTile(
      title: Text(title),
      subtitle: DropdownButton<PrivacyVisibility>(
        value: value,
        isExpanded: true,
        items: PrivacyVisibility.values
            .map((v) => DropdownMenuItem(value: v, child: Text(v.name)))
            .toList(),
        onChanged: (v) { if (v != null) onChanged(v); },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // Inject your Dio (with Bearer token) from your app locator / provider.
    return Scaffold(
      appBar: AppBar(title: const Text('Privacy')),
      body: ListView(
        children: [
          _row('Profile photo', photo, (v) => setState(() => photo = v)),
          _row('About', about, (v) => setState(() => about = v)),
          _row('Last seen', lastSeen, (v) => setState(() => lastSeen = v)),
          _row('Status', status, (v) => setState(() => status = v)),
          Padding(
            padding: const EdgeInsets.all(16),
            child: FilledButton(
              onPressed: saving ? null : () {/* call _save(dio) */},
              child: Text(saving ? 'Saving…' : 'Save'),
            ),
          ),
        ],
      ),
    );
  }
}
```

> Full chat + WebSocket flows: [`FLUTTER_CHAT.md`](./FLUTTER_CHAT.md)  
> Dedicated privacy notes for mobile: [`FLUTTER_PRIVACY.md`](./FLUTTER_PRIVACY.md)

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
| PATCH | `/chat/conversations/{id}/group/` | Update group name/avatar/`admins_only_messages` (admin only) |
| POST | `/chat/conversations/{id}/members/{user_id}/remove/` | Remove member (admin only) |
| GET | `/chat/conversations/{id}/messages/?before=100` | Get messages (paginated; excludes your "delete for me") |
| GET | `/chat/conversations/{id}/messages/?around=88` | Messages centered on id 88 (search jump) |
| GET | `/chat/conversations/{id}/messages/search/?q=` | Search in this chat (min 2 chars) |
| GET | `/chat/messages/search/?q=` | Search messages in all your chats |
| POST | `/chat/conversations/{id}/send/` | Send message (multipart; optional `reply_to_id`, `mentioned_user_ids`, `mention_everyone`) |
| POST | `/chat/conversations/{id}/messages/{message_id}/forward/` | Forward to other chats `{ "conversation_ids": [2,3] }` (max 10) |
| GET | `/chat/conversations/{id}/draft/` | Get unsent draft (`null` if none) |
| PUT | `/chat/conversations/{id}/draft/` | Save draft `{ "content", "reply_to_id"? }` — blank content clears |
| DELETE | `/chat/conversations/{id}/draft/` | Clear draft |
| DELETE | `/chat/conversations/{id}/messages/{message_id}/` | Delete for me **or** everyone |
| POST | `/chat/conversations/{id}/messages/{message_id}/react/` | Add/toggle emoji reaction |
| PATCH | `/chat/conversations/{id}/messages/{message_id}/edit/` | Edit own text message within 15 minutes `{ "content" }` |
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
- Block works for **group** chats too — it blocks the chat for you only, not the group for everyone.

### Report user or chat

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

`conversation_id` is optional and turns a user report into a **chat report** by linking the offending conversation. It accepts 1:1 **and group** conversation IDs, so you can report a group member from the group info screen. You must be a participant of that conversation or the API returns `403`.

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

Group mentions (optional; ignored in 1:1):

```http
POST /chat/conversations/3/send/
Content-Type: multipart/form-data

content=Hey @Priya
message_type=text
mentioned_user_ids=2
mention_everyone=false
```

See **[`FLUTTER_GROUP_MENTIONS_ADMINS.md`](./FLUTTER_GROUP_MENTIONS_ADMINS.md)**.

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

### Edit a message (15-minute window)

```http
PATCH /chat/conversations/1/messages/42/edit/
Content-Type: application/json

{ "content": "Updated text" }
```

See **[`FLUTTER_EDIT_MESSAGE.md`](./FLUTTER_EDIT_MESSAGE.md)** for models, Dio, and UI walkthrough.

### Group admin

Group creator is admin (`created_by` / `is_admin: true` on conversation).

```http
PATCH /chat/conversations/1/group/
Content-Type: multipart/form-data

group_name=Family Chat
group_avatar=<optional file>
admins_only_messages=true
```

JSON also works: `{ "admins_only_messages": true }`. Non-admins receive **403** on send/forward while this is on. See **[`FLUTTER_GROUP_MENTIONS_ADMINS.md`](./FLUTTER_GROUP_MENTIONS_ADMINS.md)**.

```http
POST /chat/conversations/1/members/5/remove/
```

---

## Stories / Status APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stories/feed/` | My + contacts' statuses (respects `status_privacy`) |
| POST | `/stories/create/` | Create status (multipart) |
| POST | `/stories/{id}/view/` | Mark status viewed (`403` if author's privacy blocks you) |
| DELETE | `/stories/{id}/delete/` | Delete own status |
| GET | `/stories/{id}/viewers/` | Who viewed (owner only) |

`status_privacy: nobody` hides the author from other users' feeds. See [Privacy settings](#privacy-settings-profile-photo--about--last-seen--status) and [`FLUTTER_PRIVACY.md`](./FLUTTER_PRIVACY.md).

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
