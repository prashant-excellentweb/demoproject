# ChatApp — Flutter Reply, Forward & Draft Guide

Inline **replies**, **forward** to other chats, and **per-conversation drafts**.

Use this with [`FLUTTER_API.md`](./FLUTTER_API.md) (all endpoints) and [`FLUTTER_CHAT.md`](./FLUTTER_CHAT.md) (REST vs WebSocket, send/list, typing).

Sending is still **REST only**. WebSocket delivers the new message (including `reply_to` / `is_forwarded`) after the server saves it.

---

## What to build in Flutter

| Screen / area | Behavior |
|---------------|----------|
| **Message bubble** | Quote strip when `reply_to != null`; italic “Forwarded” when `is_forwarded` |
| **Message actions** | Reply → set composer quote; Forward → pick chats (max 10) |
| **Composer** | Reply banner above the input; send with `reply_to_id` |
| **Composer** | Debounced `PUT …/draft/` while typing; restore on chat open |
| **Inbox row** | Subtitle `Draft: …` when `conversation.draft` is present |

---

## API summary

| Method | Endpoint | Notes |
|--------|----------|-------|
| `POST` | `/chat/conversations/{id}/send/` | Optional `reply_to_id` (multipart or form field) |
| `POST` | `/chat/conversations/{id}/messages/{msgId}/forward/` | `{ "conversation_ids": [2, 3] }` — max 10 |
| `GET` | `/chat/conversations/{id}/draft/` | Current user’s draft or `null` |
| `PUT` | `/chat/conversations/{id}/draft/` | `{ "content", "reply_to_id"? }` — blank `content` clears |
| `DELETE` | `/chat/conversations/{id}/draft/` | Clear draft |
| `GET` | `/chat/conversations/` | Each chat includes `draft` (or `null`) |

Envelope is always `{ success, message, data }`.

---

## 1. Inline reply

### Send a reply

```http
POST /chat/conversations/1/send/
Authorization: Bearer <access>
Content-Type: multipart/form-data

content=Thanks for that!
message_type=text
reply_to_id=42
```

Media replies work the same: attach `file` + `message_type` and still pass `reply_to_id`.

Rules:

- Target must be in the **same** conversation and **not deleted**.
- Invalid / missing target → `400`.
- Owner of the reply is the sender; the quoted user does not need to approve.

### `reply_to` on every message

```json
{
  "id": 99,
  "conversation": 1,
  "sender": { "id": 1, "display_name": "Alex" },
  "message_type": "text",
  "content": "Thanks for that!",
  "reply_to": {
    "id": 42,
    "sender_id": 2,
    "sender_name": "Priya",
    "message_type": "text",
    "content": "Can you send the invoice?",
    "file_name": "",
    "is_deleted": false
  },
  "is_forwarded": false,
  "forwarded_from": null
}
```

`reply_to.content` is trimmed to **120** characters. For images/files, use `message_type` + `file_name` when `content` is empty.

If the original is later deleted-for-everyone, later payloads set `reply_to` to `null` on that message (deleted messages also drop their quote).

### Flutter: send with Dio

```dart
Future<Map<String, dynamic>> sendReply(
  Dio dio, {
  required int conversationId,
  required String content,
  int? replyToId,
  MultipartFile? file,
  String messageType = 'text',
}) async {
  final form = FormData.fromMap({
    'content': content,
    'message_type': messageType,
    if (replyToId != null) 'reply_to_id': replyToId,
    if (file != null) 'file': file,
  });
  final res = await dio.post('/chat/conversations/$conversationId/send/', data: form);
  if (res.data['success'] != true) {
    throw Exception(res.data['message'] ?? 'Send failed');
  }
  return res.data['data'] as Map<String, dynamic>;
}
```

### Composer walkthrough

1. Long-press / overflow → **Reply**.
2. Store `MessageQuote` in composer state; show a banner (“Replying to {sender_name}”).
3. On send, pass `reply_to_id`.
4. Clear the banner after success (server also clears the draft).
5. Optional: tap the quote strip → `Scrollable.ensureVisible` on the original bubble (`id` = `reply_to.id`).

Incoming replies arrive on WebSocket `type: "message"` with the same `reply_to` object. Deduplicate by `id` (REST send + WS echo).

---

## 2. Forward

### Request

```http
POST /chat/conversations/1/messages/42/forward/
Authorization: Bearer <access>
Content-Type: application/json

{ "conversation_ids": [2, 5] }
```

| Rule | Detail |
|------|--------|
| Max targets | 10 unique IDs |
| Source | Must be a participant; message must exist and not be deleted |
| Targets | You must be a participant; blocked chats fail that target only |
| File copies | Server reuses the stored file — no re-upload |
| Chain | Forward-of-a-forward still points `forwarded_from` at the **original** |

### Success (`201`)

```json
{
  "success": true,
  "message": "Message forwarded to 2 chat(s).",
  "data": {
    "forwarded": [
      {
        "id": 201,
        "conversation": 2,
        "is_forwarded": true,
        "forwarded_from": 42,
        "content": "Can you send the invoice?",
        "reply_to": null
      }
    ],
    "failed": []
  }
}
```

Partial success is possible: some IDs in `forwarded`, others in `failed: [{ "conversation_id", "error" }]`.

If **nothing** was forwarded, `success` is `false` (`400`) and `data.failed` lists why.

Each created copy is broadcast over WebSocket to that conversation’s participants.

### Flutter: forward with Dio

```dart
Future<ForwardResult> forwardMessage(
  Dio dio, {
  required int sourceConversationId,
  required int messageId,
  required List<int> conversationIds,
}) async {
  final res = await dio.post(
    '/chat/conversations/$sourceConversationId/messages/$messageId/forward/',
    data: {'conversation_ids': conversationIds},
  );
  final body = res.data as Map<String, dynamic>;
  if (body['success'] != true) {
    throw Exception(body['message'] ?? 'Forward failed');
  }
  final data = body['data'] as Map<String, dynamic>;
  return ForwardResult.fromJson(data);
}

class ForwardResult {
  final List<Map<String, dynamic>> forwarded;
  final List<ForwardFailure> failed;
  ForwardResult({required this.forwarded, required this.failed});

  factory ForwardResult.fromJson(Map<String, dynamic> j) => ForwardResult(
        forwarded: List<Map<String, dynamic>>.from(j['forwarded'] ?? []),
        failed: (j['failed'] as List? ?? [])
            .map((e) => ForwardFailure.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class ForwardFailure {
  final int conversationId;
  final String error;
  ForwardFailure({required this.conversationId, required this.error});

  factory ForwardFailure.fromJson(Map<String, dynamic> j) => ForwardFailure(
        conversationId: j['conversation_id'],
        error: j['error'] ?? '',
      );
}
```

### Picker walkthrough

1. Load `GET /chat/conversations/?filter=all` (skip current chat and `is_blocked`).
2. Multi-select up to 10.
3. `POST …/forward/`.
4. If `failed` is non-empty, snackbar the first error; still refresh the inbox if `forwarded` is non-empty.
5. Render `is_forwarded` as a small italic label on the copy. `forwarded_from` is the original message **id** (integer), not a nested object.

Do **not** send forwards over WebSocket.

---

## 3. Draft message

One draft per **user + conversation**. It can keep a pending `reply_to`.

### Get

```http
GET /chat/conversations/1/draft/
```

`data` is `null` when there is no draft.

```json
{
  "success": true,
  "message": "Draft fetched successfully.",
  "data": {
    "conversation": 1,
    "content": "I'll send it after lunch",
    "reply_to": {
      "id": 42,
      "sender_id": 2,
      "sender_name": "Priya",
      "message_type": "text",
      "content": "Can you send the invoice?",
      "file_name": "",
      "is_deleted": false
    },
    "updated_at": "2026-09-19T12:00:00Z"
  }
}
```

Inbox list already includes the same object as `conversation.draft` (`null` if empty). You can skip `GET` if you trust the list payload, or `GET` when opening a chat for the latest text.

### Save / clear

```http
PUT /chat/conversations/1/draft/
Content-Type: application/json

{ "content": "I'll send it after lunch", "reply_to_id": 42 }
```

- Non-blank `content` upserts the draft.
- Blank / whitespace `content` **clears** the row (`data: null`).
- Invalid `reply_to_id` → `400`.
- `DELETE /chat/conversations/1/draft/` also clears.

### Auto-clear on send

`POST …/send/` deletes that user’s draft for the chat. You do not need a separate `DELETE` after a successful send.

### Flutter: debounce save

```dart
Timer? _draftTimer;

void onComposerChanged({
  required Dio dio,
  required int conversationId,
  required String text,
  int? replyToId,
}) {
  _draftTimer?.cancel();
  _draftTimer = Timer(const Duration(milliseconds: 500), () async {
    await dio.put(
      '/chat/conversations/$conversationId/draft/',
      data: {
        'content': text,
        'reply_to_id': replyToId,
      },
    );
  });
}

/// Call when opening a chat (after GET messages).
Future<void> restoreDraft(Dio dio, int conversationId, void Function(String, int?) apply) async {
  final res = await dio.get('/chat/conversations/$conversationId/draft/');
  final data = res.data['data'];
  if (data is Map<String, dynamic>) {
    apply(
      data['content'] as String? ?? '',
      (data['reply_to'] as Map?)?['id'] as int?,
    );
  } else {
    apply('', null);
  }
}
```

### Draft walkthrough

1. Open chat → `GET …/draft/` → fill `TextEditingController` + reply banner.
2. Skip the first autosave so you do not immediately `PUT` the same text.
3. Debounce 400–600 ms on text / reply changes.
4. Inbox: if `draft != null`, show green/italic `Draft: ${draft.content}` instead of last-message preview.
5. Successful send → clear local composer; server cleared the row.

---

## Dart models to add

```dart
class MessageQuote {
  final int id;
  final int senderId;
  final String senderName;
  final String messageType;
  final String content;
  final String fileName;
  final bool isDeleted;

  MessageQuote.fromJson(Map<String, dynamic> j)
      : id = j['id'],
        senderId = j['sender_id'],
        senderName = j['sender_name'] ?? '',
        messageType = j['message_type'] ?? 'text',
        content = j['content'] ?? '',
        fileName = j['file_name'] ?? '',
        isDeleted = j['is_deleted'] == true;
}

class MessageDraft {
  final int conversationId;
  final String content;
  final MessageQuote? replyTo;
  final DateTime? updatedAt;

  MessageDraft.fromJson(Map<String, dynamic> j)
      : conversationId = j['conversation'],
        content = j['content'] ?? '',
        replyTo = j['reply_to'] is Map<String, dynamic>
            ? MessageQuote.fromJson(j['reply_to'])
            : null,
        updatedAt = j['updated_at'] != null ? DateTime.tryParse(j['updated_at']) : null;
}
```

Extend `MessageModel` with:

```dart
final MessageQuote? replyTo;
final bool isForwarded;
final int? forwardedFrom; // original message id
```

Extend `ConversationModel` with `MessageDraft? draft`.

---

## UI checklist

- [ ] Quote strip on bubbles; tap scrolls to original (optional)
- [ ] “Forwarded” label when `is_forwarded == true`
- [ ] Reply action sets composer banner + includes `reply_to_id` on send (text and media)
- [ ] Forward picker (max 10) → handle `failed` array
- [ ] Draft autosave debounced; skip first save after restore
- [ ] Draft restored when reopening the chat
- [ ] Inbox shows `Draft: …` when `draft != null`
- [ ] Deduplicate REST + WS messages by `id`

---

## Manual test plan

1. Reply to a text message → both users see the quote (WS).
2. Reply to a deleted message → send returns `400`.
3. Forward to two chats → both copies have `is_forwarded: true` and the same `forwarded_from`.
4. Forward while one target is blocked → partial success + `failed` entry.
5. Type without sending → leave chat → reopen → text (and reply banner) restored.
6. Send the draft → `GET …/draft/` is `null`; inbox preview is the sent message.

---

## Related files (backend / web)

| Area | Path |
|------|------|
| Models | `backend/apps/chat/models.py` (`Message.reply_to`, `is_forwarded`, `MessageDraft`) |
| Service | `backend/apps/chat/services/message_service.py` |
| Draft repo | `backend/apps/chat/repositories/draft_repository.py` |
| Web composer | `frontend/src/components/ChatWindow.tsx` |
| Web bubble | `frontend/src/components/MessageBubble.tsx` |
| Web picker | `frontend/src/components/ForwardPicker.tsx` |
| OpenAPI | http://localhost:9000/api/docs/ |
