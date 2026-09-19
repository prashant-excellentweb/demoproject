# ChatApp — Flutter Edit Message Guide

Edit **your own text messages** within **15 minutes** of sending.

Use with [`FLUTTER_API.md`](./FLUTTER_API.md) and [`FLUTTER_CHAT.md`](./FLUTTER_CHAT.md). Save via REST; other clients get the change on WebSocket `message_updated` (same event as reactions).

---

## What to build in Flutter

| Screen / area | Behavior |
|---------------|----------|
| **Own text bubble** | Show **Edit** for 15 minutes after `created_at` |
| **Inline editor** | Replace the text with a field; Save / Cancel; Enter saves, Escape cancels |
| **All bubbles** | Show italic `edited` when `is_edited == true` |
| **Inbox preview** | After edit, last-message text updates on next list refresh / `message_updated` |

---

## API

```http
PATCH /chat/conversations/{conversationId}/messages/{messageId}/edit/
Authorization: Bearer <access>
Content-Type: application/json

{ "content": "Updated text" }
```

| Rule | Result |
|------|--------|
| Not the sender | `403` |
| Chat blocked by you | `403` |
| Not a text message | `400` |
| Deleted message | `400` |
| Older than 15 minutes | `400` — *Edit window expired…* |
| Blank content | `400` |
| Same text as before | `200`, `edited_at` **unchanged** |

Default window: `MESSAGE_EDIT_WINDOW_MINUTES = 15`.

### Success

```json
{
  "success": true,
  "message": "Message edited.",
  "data": {
    "id": 42,
    "content": "Updated text",
    "is_edited": true,
    "edited_at": "2026-09-19T13:05:00Z",
    "created_at": "2026-09-19T12:55:00Z",
    "message_type": "text"
  }
}
```

Each participant receives:

```json
{ "type": "message_updated", "message": { /* full MessageSerializer */ } }
```

Replace the bubble by `id`. Do **not** treat this as a new message.

---

## Dio

```dart
Future<Map<String, dynamic>> editMessage(
  Dio dio, {
  required int conversationId,
  required int messageId,
  required String content,
}) async {
  final res = await dio.patch(
    '/chat/conversations/$conversationId/messages/$messageId/edit/',
    data: {'content': content.trim()},
  );
  if (res.data['success'] != true) {
    throw Exception(res.data['message'] ?? 'Edit failed');
  }
  return res.data['data'] as Map<String, dynamic>;
}
```

---

## Models

Add to `MessageModel`:

```dart
final bool isEdited;
final DateTime? editedAt;

// in fromJson:
isEdited: j['is_edited'] == true,
editedAt: j['edited_at'] != null ? DateTime.tryParse(j['edited_at']) : null,
```

```dart
const editWindow = Duration(minutes: 15);

bool canEditMessage({
  required bool isMine,
  required String messageType,
  required bool isDeleted,
  required DateTime createdAt,
  DateTime? now,
}) {
  if (!isMine || isDeleted || messageType != 'text') return false;
  return (now ?? DateTime.now()).difference(createdAt) < editWindow;
}
```

Schedule a `Timer` for `editWindow - age` to hide the Edit action when the window closes.

---

## Walkthrough

1. User sends a text message (`POST …/send/`).
2. For 15 minutes, their bubble shows Edit (hover / overflow).
3. Tap Edit → local `TextEditingController` with current `content`.
4. Save → `PATCH …/edit/` → replace local message with `data`.
5. Others already in the room apply `message_updated`.
6. After 15 minutes, hide Edit. A late `PATCH` still fails with `400`.

Media (image/video/file/audio) **cannot** be edited. Delete + resend instead.

---

## UI checklist

- [ ] Edit only on **your** text messages, not deleted, within 15 minutes
- [ ] `edited` label when `is_edited`
- [ ] Handle `403` / `400` with `message` from the envelope
- [ ] Deduplicate: REST response and WS `message_updated` share the same `id`
- [ ] Inbox last-message preview updates after an edit of the latest message

---

## Manual test plan

1. Send “hello” → Edit to “hello there” within a minute → both users see new text + `edited`.
2. Wait 15+ minutes → Edit hidden; `PATCH` returns `400`.
3. Other user’s bubble has no Edit.
4. Image message has no Edit.
5. Edit after blocking the chat → `403`.
6. Reacting to a message still uses `message_updated` — replace in place, don’t append.

---

## Related files

| Area | Path |
|------|------|
| Window setting | `backend/config/settings.py` → `MESSAGE_EDIT_WINDOW_MINUTES` |
| Service | `backend/apps/chat/services/message_service.py` → `edit_message` |
| Endpoint | `PATCH /api/chat/conversations/{id}/messages/{id}/edit/` |
| Web UI | `frontend/src/components/MessageBubble.tsx` |
| OpenAPI | http://localhost:9000/api/docs/ |
