# Flutter Chat Guide — Conversations + WebSocket

End-to-end guide to implement WhatsApp-style chat in Flutter against this backend.

Related docs:
- Full REST reference: [`FLUTTER_API.md`](./FLUTTER_API.md)
- Swagger UI: `http://localhost:9000/api/docs/`

---

## 1. Architecture (how chat works)

This app uses **REST for data** and **WebSocket for live updates**.

| Concern | Use | Why |
|---------|-----|-----|
| Login, profile, search users | REST | One-shot request/response |
| List chats, open history, send media | REST | Persistence, pagination, files |
| New message while chat is open | WebSocket | Instant delivery |
| Typing indicator | WebSocket | Ephemeral |
| Delete for everyone / reactions | REST + WebSocket | REST saves; WS notifies others |
| Mark as read | REST or WebSocket | Both supported |

```
Flutter app
   |
   |-- REST (Dio) --------> http://host:9000/api  (history, send, pin, etc.)
   |
   |-- WebSocket ---------> ws://host:9000/ws/chat/?token=...
          |                      |
          | join / typing / read |
          | <--- message / typing / deleted / updated
          v
     Redis + Django Channels
```

**Rule of thumb**
1. Open app → connect WebSocket once (after login).
2. Chat list → `GET /chat/conversations/`.
3. Open a chat → `GET .../messages/` + WS `join_conversation`.
4. Send message → REST `POST .../send/` (server broadcasts over WS).
5. Leave chat → WS `leave_conversation`.

Sending text/files over WebSocket is **not** supported. Always send via REST.

---

## 2. Base URLs

| Platform | REST base | WebSocket |
|----------|-----------|-----------|
| Android emulator | `http://10.0.2.2:9000/api` | `ws://10.0.2.2:9000/ws/chat/` |
| iOS simulator | `http://127.0.0.1:9000/api` | `ws://127.0.0.1:9000/ws/chat/` |
| Real device (same Wi‑Fi) | `http://<PC-LAN-IP>:9000/api` | `ws://<PC-LAN-IP>:9000/ws/chat/` |
| Production (HTTPS) | `https://api.example.com/api` | `wss://api.example.com/ws/chat/` |

Auth on every REST call (except OTP):

```http
Authorization: Bearer <access_token>
```

WebSocket auth is the JWT query param:

```
ws://10.0.2.2:9000/ws/chat/?token=<access_token>
```

If token is missing/invalid, the server closes the socket immediately.

---

## 3. Packages

```yaml
dependencies:
  dio: ^5.7.0
  web_socket_channel: ^3.0.1
  flutter_secure_storage: ^9.2.2
  connectivity_plus: ^6.0.0   # optional: reconnect on network restore
  intl: ^0.19.0               # optional: time formatting
```

---

## 4. Models (match API `data`)

Every REST response looks like:

```json
{ "success": true, "message": "...", "data": { } }
```

Always parse `data`, not the root body.

```dart
class ApiResponse<T> {
  final bool success;
  final String message;
  final T? data;

  ApiResponse({required this.success, required this.message, this.data});

  factory ApiResponse.fromJson(
    Map<String, dynamic> json,
    T Function(dynamic)? fromData,
  ) {
    return ApiResponse(
      success: json['success'] == true,
      message: json['message']?.toString() ?? '',
      data: json['data'] == null || fromData == null
          ? null
          : fromData(json['data']),
    );
  }
}

class UserModel {
  final int id;
  final String phoneNumber;
  final String displayName;
  final String about;
  final String? avatarUrl;
  final bool isOnline;
  final String? lastSeen;

  UserModel({
    required this.id,
    required this.phoneNumber,
    required this.displayName,
    required this.about,
    this.avatarUrl,
    required this.isOnline,
    this.lastSeen,
  });

  factory UserModel.fromJson(Map<String, dynamic> j) => UserModel(
        id: j['id'],
        phoneNumber: j['phone_number'] ?? '',
        displayName: j['display_name'] ?? '',
        about: j['about'] ?? '',
        avatarUrl: j['avatar_url'],
        isOnline: j['is_online'] == true,
        lastSeen: j['last_seen'],
      );

  String get name => displayName.isNotEmpty ? displayName : phoneNumber;
}

class MessageModel {
  final int id;
  final int conversationId;
  final UserModel sender;
  final String messageType; // text | image | video | pdf | document | audio
  final String content;
  final String? fileUrl;
  final String fileName;
  final int fileSize;
  final bool isRead;
  final bool isDeleted;
  final List<ReactionSummary> reactions;
  final String? myReaction;
  final String createdAt;

  MessageModel({
    required this.id,
    required this.conversationId,
    required this.sender,
    required this.messageType,
    required this.content,
    this.fileUrl,
    required this.fileName,
    required this.fileSize,
    required this.isRead,
    required this.isDeleted,
    required this.reactions,
    this.myReaction,
    required this.createdAt,
  });

  factory MessageModel.fromJson(Map<String, dynamic> j) => MessageModel(
        id: j['id'],
        conversationId: j['conversation'],
        sender: UserModel.fromJson(j['sender']),
        messageType: j['message_type'] ?? 'text',
        content: j['content'] ?? '',
        fileUrl: j['file_url'],
        fileName: j['file_name'] ?? '',
        fileSize: j['file_size'] ?? 0,
        isRead: j['is_read'] == true,
        isDeleted: j['is_deleted'] == true,
        reactions: (j['reactions'] as List? ?? [])
            .map((e) => ReactionSummary.fromJson(e))
            .toList(),
        myReaction: j['my_reaction'],
        createdAt: j['created_at'] ?? '',
      );
}

class ReactionSummary {
  final String emoji;
  final int count;
  final List<int> userIds;

  ReactionSummary({required this.emoji, required this.count, required this.userIds});

  factory ReactionSummary.fromJson(Map<String, dynamic> j) => ReactionSummary(
        emoji: j['emoji'] ?? '',
        count: j['count'] ?? 0,
        userIds: List<int>.from(j['user_ids'] ?? []),
      );
}

class ConversationModel {
  final int id;
  final List<UserModel> participants;
  final bool isGroup;
  final String groupName;
  final String? groupAvatarUrl;
  final int? createdBy;
  final bool isAdmin;
  final bool isFavourite;
  final bool isArchived;
  final bool isBlocked;
  final bool isPinned;
  final MessageModel? lastMessage;
  final int unreadCount;
  final String updatedAt;

  ConversationModel({
    required this.id,
    required this.participants,
    required this.isGroup,
    required this.groupName,
    this.groupAvatarUrl,
    this.createdBy,
    required this.isAdmin,
    required this.isFavourite,
    required this.isArchived,
    required this.isBlocked,
    required this.isPinned,
    this.lastMessage,
    required this.unreadCount,
    required this.updatedAt,
  });

  factory ConversationModel.fromJson(Map<String, dynamic> j) => ConversationModel(
        id: j['id'],
        participants: (j['participants'] as List? ?? [])
            .map((e) => UserModel.fromJson(e))
            .toList(),
        isGroup: j['is_group'] == true,
        groupName: j['group_name'] ?? '',
        groupAvatarUrl: j['group_avatar_url'],
        createdBy: j['created_by'],
        isAdmin: j['is_admin'] == true,
        isFavourite: j['is_favourite'] == true,
        isArchived: j['is_archived'] == true,
        isBlocked: j['is_blocked'] == true,
        isPinned: j['is_pinned'] == true,
        lastMessage: j['last_message'] == null
            ? null
            : MessageModel.fromJson(j['last_message']),
        unreadCount: j['unread_count'] ?? 0,
        updatedAt: j['updated_at'] ?? '',
      );

  /// Direct chat title = other participant's name
  String title(int myUserId) {
    if (isGroup) return groupName;
    final other = participants.where((p) => p.id != myUserId).firstOrNull;
    return other?.name ?? 'Chat';
  }
}
```

---

## 5. Conversation REST APIs (implement these)

### 5.1 Chat list (inbox)

```http
GET /chat/conversations/?filter=all
```

| `filter` | UI tab |
|----------|--------|
| `all` | All (default; excludes archived; pinned → favourites → recent) |
| `unread` | Unread |
| `groups` | Groups |
| `favourites` | Favourites |
| `archived` | Archived |
| `blocked` | Blocked |

```dart
Future<List<ConversationModel>> fetchConversations({String filter = 'all'}) async {
  final res = await dio.get('/chat/conversations/', queryParameters: {'filter': filter});
  final body = res.data as Map<String, dynamic>;
  if (body['success'] != true) throw Exception(body['message']);
  final list = body['data'] as List;
  return list.map((e) => ConversationModel.fromJson(e)).toList();
}
```

### 5.2 Start chats

```http
POST /chat/conversations/direct/
{ "user_id": 2 }

POST /chat/conversations/group/
{ "group_name": "Family", "participant_ids": [2, 3] }
```

Both return a `Conversation` in `data`. Open that chat screen with `data.id`.

### 5.3 Open chat history

```http
GET /chat/conversations/{id}/messages/
GET /chat/conversations/{id}/messages/?before={oldestMessageId}
```

- Newest-first from API → reverse for UI chronological list.
- Paginate older messages with `before`.

```dart
Future<List<MessageModel>> fetchMessages(int conversationId, {int? before}) async {
  final res = await dio.get(
    '/chat/conversations/$conversationId/messages/',
    queryParameters: before == null ? null : {'before': before},
  );
  final body = res.data as Map<String, dynamic>;
  final list = (body['data'] as List).map((e) => MessageModel.fromJson(e)).toList();
  return list.reversed.toList(); // oldest → newest for ListView
}
```

### 5.4 Send message (REST only → then WS delivers to others)

```http
POST /chat/conversations/{id}/send/
Content-Type: multipart/form-data
```

| Field | When |
|-------|------|
| `content` | Text (and captions) |
| `message_type` | `text` \| `image` \| `video` \| `pdf` \| `document` \| `audio` |
| `file` | Media / documents |

```dart
Future<MessageModel> sendText(int conversationId, String text) async {
  final form = FormData.fromMap({
    'content': text,
    'message_type': 'text',
  });
  final res = await dio.post('/chat/conversations/$conversationId/send/', data: form);
  return MessageModel.fromJson(res.data['data']);
}

Future<MessageModel> sendFile(int conversationId, String path, String type) async {
  final form = FormData.fromMap({
    'file': await MultipartFile.fromFile(path),
    'message_type': type, // image | video | pdf | document | audio
  });
  final res = await dio.post('/chat/conversations/$conversationId/send/', data: form);
  return MessageModel.fromJson(res.data['data']);
}
```

**Blocked chat:** send returns `403`. Show “Unblock to send” and call unblock API.

### 5.5 Chat actions (list ⋮ menu)

| Action | Endpoint | Body |
|--------|----------|------|
| Favourite toggle | `POST /chat/conversations/{id}/favourite/` | — |
| Archive | `POST /chat/conversations/{id}/archive/` | `{ "action": "archive" \| "unarchive" }` |
| Block | `POST /chat/conversations/{id}/block/` | `{ "action": "block" \| "unblock" }` |
| Pin | `POST /chat/conversations/{id}/pin/` | `{ "action": "pin" \| "unpin" }` |

Each returns the updated conversation in `data` (`is_pinned`, `is_blocked`, …).

### 5.6 Delete / react / read

```http
DELETE /chat/conversations/{id}/messages/{messageId}/
{ "delete_for": "me" | "everyone" }

POST /chat/conversations/{id}/messages/{messageId}/react/
{ "emoji": "👍" }

POST /chat/conversations/{id}/read/
```

Allowed reactions: `👍` `❤️` `😂` `😮` `😢` `🙏` `🔥` `👏`

| Delete mode | Who | UI | WebSocket |
|-------------|-----|----|-----------|
| `me` | Any participant | Remove from your list only | **No** broadcast |
| `everyone` | Sender or group admin | Show “This message was deleted” | `message_deleted` |

### 5.7 Report user (direct chat)

```http
POST /auth/users/{userId}/report/
{
  "reason": "spam",
  "details": "optional",
  "conversation_id": 1
}
```

`reason`: `spam` | `harassment` | `inappropriate` | `fake` | `other`

---

## 6. WebSocket — connect and stay alive

### 6.1 Service skeleton

```dart
import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

class ChatSocketService {
  WebSocketChannel? _channel;
  StreamSubscription? _sub;
  final _controller = StreamController<Map<String, dynamic>>.broadcast();

  Stream<Map<String, dynamic>> get events => _controller.stream;
  bool get isConnected => _channel != null;

  void connect(String wsBaseUrl, String accessToken) {
    disconnect();
    final uri = Uri.parse('$wsBaseUrl?token=$accessToken');
    _channel = WebSocketChannel.connect(uri);
    _sub = _channel!.stream.listen(
      (raw) {
        final data = jsonDecode(raw as String) as Map<String, dynamic>;
        _controller.add(data);
      },
      onDone: () {
        // reconnect after short delay (keep token fresh)
        Future.delayed(const Duration(seconds: 3), () {
          if (_channel != null) connect(wsBaseUrl, accessToken);
        });
      },
      onError: (_) {
        Future.delayed(const Duration(seconds: 3), () {
          connect(wsBaseUrl, accessToken);
        });
      },
    );
  }

  void _send(Map<String, dynamic> payload) {
    _channel?.sink.add(jsonEncode(payload));
  }

  void joinConversation(int conversationId) {
    _send({'action': 'join_conversation', 'conversation_id': conversationId});
  }

  void leaveConversation() {
    _send({'action': 'leave_conversation'});
  }

  void sendTyping({required bool isTyping}) {
    _send({'action': 'typing', 'is_typing': isTyping});
  }

  void markRead(int conversationId) {
    _send({'action': 'mark_read', 'conversation_id': conversationId});
  }

  void disconnect() {
    _sub?.cancel();
    _channel?.sink.close();
    _channel = null;
  }

  void dispose() {
    disconnect();
    _controller.close();
  }
}
```

Connect **once after login**, dispose on logout.

### 6.2 Client → server actions

| Action | Payload | When to call |
|--------|---------|--------------|
| `join_conversation` | `{ "action": "join_conversation", "conversation_id": 1 }` | Enter chat screen |
| `leave_conversation` | `{ "action": "leave_conversation" }` | Leave chat screen / dispose |
| `typing` | `{ "action": "typing", "is_typing": true\|false }` | Text field changes (debounce) |
| `mark_read` | `{ "action": "mark_read", "conversation_id": 1 }` | Chat opened / new msg while open |

You must `join_conversation` before typing events work for that room.

### 6.3 Server → client events

| `type` | Payload | What to do in UI |
|--------|---------|------------------|
| `message` | `{ "type":"message", "message": { ... } }` | Append to open chat if `message.conversation` matches; else bump chat list preview + unread |
| `message_deleted` | `{ "type":"message_deleted", "message": { ... } }` | Replace bubble with deleted state (`is_deleted: true`) |
| `message_updated` | `{ "type":"message_updated", "message": { ... } }` | Replace message (reactions changed) |
| `typing` | `{ "type":"typing", "user_id", "user_name", "is_typing" }` | Print “X is typing…” (hide after ~3s) |
| `read` | `{ "type":"read", ... }` | Optional read-receipt UI |

Example event:

```json
{
  "type": "message",
  "message": {
    "id": 101,
    "conversation": 1,
    "sender": {
      "id": 2,
      "phone_number": "+911234567890",
      "display_name": "Priya",
      "about": "Hey there!",
      "avatar_url": null,
      "is_online": true,
      "last_seen": null
    },
    "message_type": "text",
    "content": "Hello!",
    "file_url": null,
    "file_name": "",
    "file_size": 0,
    "is_read": false,
    "is_deleted": false,
    "reactions": [],
    "my_reaction": null,
    "created_at": "2026-07-15T10:30:00Z"
  }
}
```

**Delivery groups**
- While you **joined** a conversation → you get live room events.
- Even if you did **not** join (you're on chat list) → new messages are still pushed to your personal `user_{id}` group, so inbox can update in real time.

---

## 7. Screen scenarios (implement in this order)

### Scenario A — Login → Inbox

1. `POST /auth/verify-otp/` → store `access` + `refresh` + `user`.
2. `ChatSocketService.connect(wsUrl, access)`.
3. `GET /chat/conversations/?filter=all`.
4. Listen to socket `type == message` → update that row’s `last_message` / `unread_count` (or refetch list).

Sort UI: pinned first, then favourites, then `updated_at` / last message time (server already sorts).

### Scenario B — Open a chat

```
openChat(conversationId):
  1. GET /chat/conversations/{id}/messages/   → set state
  2. socket.joinConversation(id)
  3. socket.markRead(id)  OR  POST /chat/conversations/{id}/read/
  4. subscribe to events for this screen
  5. on dispose → socket.leaveConversation()
```

```dart
class ChatScreen extends StatefulWidget {
  final int conversationId;
  final int myUserId;
  // ...
}

class _ChatScreenState extends State<ChatScreen> {
  final messages = <MessageModel>[];
  String? typingName;
  StreamSubscription? _sub;
  Timer? _typingHide;

  @override
  void initState() {
    super.initState();
    _load();
    chatSocket.joinConversation(widget.conversationId);
    chatSocket.markRead(widget.conversationId);
    _sub = chatSocket.events.listen(_onEvent);
  }

  Future<void> _load() async {
    final list = await api.fetchMessages(widget.conversationId);
    setState(() {
      messages
        ..clear()
        ..addAll(list);
    });
  }

  void _onEvent(Map<String, dynamic> event) {
    final type = event['type'];
    if (type == 'message') {
      final msg = MessageModel.fromJson(event['message']);
      if (msg.conversationId != widget.conversationId) return;
      if (messages.any((m) => m.id == msg.id)) return; // dedupe vs REST echo
      setState(() => messages.add(msg));
      chatSocket.markRead(widget.conversationId);
    } else if (type == 'message_deleted' || type == 'message_updated') {
      final msg = MessageModel.fromJson(event['message']);
      final i = messages.indexWhere((m) => m.id == msg.id);
      if (i >= 0) setState(() => messages[i] = msg);
    } else if (type == 'typing') {
      if (event['user_id'] == widget.myUserId) return;
      setState(() => typingName = event['is_typing'] == true ? event['user_name'] : null);
      _typingHide?.cancel();
      if (event['is_typing'] == true) {
        _typingHide = Timer(const Duration(seconds: 3), () {
          if (mounted) setState(() => typingName = null);
        });
      }
    }
  }

  Future<void> _send(String text) async {
    final msg = await api.sendText(widget.conversationId, text);
    // Optimistic: add only if WS hasn't already delivered same id
    if (!messages.any((m) => m.id == msg.id)) {
      setState(() => messages.add(msg));
    }
  }

  void _onTextChanged(String value) {
    chatSocket.sendTyping(isTyping: value.isNotEmpty);
  }

  @override
  void dispose() {
    _sub?.cancel();
    _typingHide?.cancel();
    chatSocket.leaveConversation();
    chatSocket.sendTyping(isTyping: false);
    super.dispose();
  }
}
```

### Scenario C — Send message flow

```
User taps Send
    │
    ▼
POST /chat/conversations/{id}/send/   (multipart)
    │
    ├─► Your app: add message from REST response (or wait for WS)
    │
    └─► Server broadcasts WS { type: "message", message: {...} }
            │
            ├─► Other users in conversation_group (open chat)
            └─► Other users in user_group (inbox list)
```

Deduplicate by `message.id` because you may get both the REST response and the WS event.

### Scenario D — Typing indicator

1. On text change → `sendTyping(true)` (throttle ~300–500 ms).
2. On clear / send / dispose → `sendTyping(false)`.
3. On receive `typing` for other user → show banner; auto-hide after 3s.

Requires prior `join_conversation`.

### Scenario E — Delete for everyone

```
DELETE .../messages/{id}/  { "delete_for": "everyone" }
    → update local bubble from response
    → others get WS message_deleted
```

Delete for me: remove locally only; **do not** expect a WS event.

### Scenario F — Reactions

```
POST .../messages/{id}/react/  { "emoji": "❤️" }
    → replace message from REST data
    → others get WS message_updated
```

### Scenario G — Chat list live update

While on inbox (no join):

```dart
chatSocket.events.listen((event) {
  if (event['type'] == 'message') {
    final msg = MessageModel.fromJson(event['message']);
    // find conversation by msg.conversationId
    // set lastMessage = msg
    // if not active chat → unreadCount++
    // move chat to top (respect pin/favourite order, or refetch)
  }
});
```

Simplest reliable approach: on any `message` / `message_deleted`, call `fetchConversations(filter)` again.

---

## 8. What REST vs WebSocket for each feature

| Feature | REST | WebSocket |
|---------|------|-----------|
| List conversations | ✅ required | Optional refresh on `message` |
| Load history | ✅ required | — |
| Send text/file | ✅ required | Receives as `message` |
| Typing | — | ✅ `typing` action + event |
| Join/leave room | — | ✅ required for typing / active room |
| Mark read | ✅ and/or ✅ WS `mark_read` | Prefer WS when chat open |
| Delete for me | ✅ | — |
| Delete for everyone | ✅ | ✅ `message_deleted` |
| React | ✅ | ✅ `message_updated` |
| Pin / archive / block / favourite | ✅ | — |
| Report user | ✅ | — |
| Online presence | Profile fields | Set automatically on WS connect/disconnect (`is_online`, `last_seen`) |

---

## 9. Suggested Flutter folder layout

```
lib/
  core/
    api_client.dart          # Dio + JWT interceptor + refresh
    chat_socket_service.dart # WebSocket singleton
  models/
    user.dart
    message.dart
    conversation.dart
  repositories/
    auth_repository.dart
    chat_repository.dart     # all /chat/... REST calls
  providers/ or blocs/
    auth_cubit.dart
    conversation_list_cubit.dart
    chat_cubit.dart          # open chat + WS listeners
  screens/
    login_screen.dart
    chat_list_screen.dart
    chat_screen.dart
    new_chat_screen.dart
```

Lifecycle:

```
App start
  → if token → connect socket + load inbox
Login success
  → save tokens → connect socket → go ChatList
Logout / delete account
  → disconnect socket → clear tokens
```

---

## 10. Token refresh + socket

1. Dio interceptor refreshes access token via `POST /auth/token/refresh/`.
2. After a successful refresh, **reconnect** WebSocket with the new access token (old JWT may close the socket).
3. On 401 that cannot refresh → logout + disconnect socket.

---

## 11. Checklist for a working Flutter chat

- [ ] OTP login stores access/refresh/user
- [ ] Dio base URL + Bearer header
- [ ] `GET /chat/conversations/` with filter tabs
- [ ] Direct + group create
- [ ] Open chat → load messages → reverse order
- [ ] WebSocket connect with `?token=`
- [ ] `join_conversation` / `leave_conversation` on chat screen
- [ ] Send via multipart REST; dedupe WS `message`
- [ ] Typing send + show
- [ ] `mark_read` when viewing chat
- [ ] Delete me / everyone + react
- [ ] Pin / archive / block / favourite from chat menu
- [ ] Blocked state disables composer
- [ ] Inbox updates on background WS `message`
- [ ] Reconnect on disconnect / token refresh
- [ ] Android cleartext / network security if using `http`/`ws` on device

---

## 12. Quick Dio helpers

```dart
final dio = Dio(BaseOptions(
  baseUrl: 'http://10.0.2.2:9000/api',
  headers: {'Authorization': 'Bearer $accessToken'},
));

// Inbox
await dio.get('/chat/conversations/', queryParameters: {'filter': 'all'});

// Open / create
await dio.post('/chat/conversations/direct/', data: {'user_id': 2});

// History
await dio.get('/chat/conversations/1/messages/');

// Send
await dio.post(
  '/chat/conversations/1/send/',
  data: FormData.fromMap({'content': 'Hi', 'message_type': 'text'}),
);

// Pin
await dio.post('/chat/conversations/1/pin/', data: {'action': 'pin'});

// React
await dio.post('/chat/conversations/1/messages/42/react/', data: {'emoji': '👍'});

// Delete for everyone
await dio.delete(
  '/chat/conversations/1/messages/42/',
  data: {'delete_for': 'everyone'},
);
```

WebSocket URL for emulator:

```
ws://10.0.2.2:9000/ws/chat/?token=<access_token>
```

Dev OTP (if enabled on server): `111111`

---

## 13. Common mistakes

1. **Sending chat over WebSocket** — not supported; use REST send.
2. **Forgetting `join_conversation`** — typing never appears for others.
3. **Not deduping message ids** — bubbles appear twice (REST + WS).
4. **Using wrong host on emulator** — use `10.0.2.2`, not `localhost`.
5. **Expecting WS for delete-for-me** — only your client should remove it.
6. **Leaving socket connected with expired token** — reconnect after refresh.
7. **Not leaving conversation** — typing continues into the next chat.

---

For auth, profile, stories, and full endpoint tables, see [`FLUTTER_API.md`](./FLUTTER_API.md).
