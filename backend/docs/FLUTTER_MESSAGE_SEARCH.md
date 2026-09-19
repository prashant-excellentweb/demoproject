# ChatApp — Flutter Message Search Guide

**In-chat** search (one conversation) and **global** search (all chats you participate in).

Use with [`FLUTTER_API.md`](./FLUTTER_API.md) and [`FLUTTER_CHAT.md`](./FLUTTER_CHAT.md). Search is REST only. Jumping to a hit uses `GET …/messages/?around={id}`.

---

## What to build in Flutter

| Screen / area | Behavior |
|---------------|----------|
| **Chat header** | Search icon → bar in that chat; min 2 characters |
| **In-chat results** | Count + up/down to older/newer matches; highlight the bubble |
| **Inbox search** | Existing name filter **plus** a **Messages** section from global search |
| **Tap a global hit** | Open that conversation and load history around the message |

---

## API summary

| Method | Endpoint | Scope |
|--------|----------|--------|
| `GET` | `/chat/conversations/{id}/messages/search/?q=` | One chat |
| `GET` | `/chat/messages/search/?q=` | All chats you are in |
| `GET` | `/chat/conversations/{id}/messages/?around={messageId}` | 50 messages centered on a hit (jump) |

Query params (search):

| Param | Required | Notes |
|-------|----------|--------|
| `q` | yes | Trimmed; **min 2**, max 100 characters |
| `before` | no | Cursor: last hit’s `id` (older page) |
| `limit` | no | Default 30, max 50 |

Shorter than 2 characters → `results: []` (not an error).

### What is searched

- `content` (text + captions)
- `file_name` (documents / media names)
- Case-insensitive `icontains`

Excluded: deleted-for-everyone, **delete for me** (hidden), chats you are not in.

Newest match first.

---

## Response

```json
{
  "success": true,
  "message": "Search results fetched.",
  "data": {
    "query": "invoice",
    "has_more": true,
    "results": [
      {
        "id": 88,
        "conversation": 3,
        "message_type": "text",
        "content": "I'll send the invoice after lunch",
        "file_name": "",
        "snippet": "I'll send the invoice after lunch",
        "created_at": "2026-09-19T12:00:00Z",
        "sender": { "id": 2, "display_name": "Priya", "avatar_url": null },
        "chat": {
          "id": 3,
          "is_group": false,
          "group_name": "",
          "group_avatar_url": null,
          "name": "Priya",
          "participants": [ /* UserPublic objects */ ]
        }
      }
    ]
  }
}
```

`snippet` is a short window around the first match (with `…` if clipped). Use it in the inbox list; use `content` in the bubble.

`has_more` is true when this page is full — pass `before=<last result id>` for the next page.

---

## Dio

```dart
Future<MessageSearchPage> searchInChat(Dio dio, int conversationId, String q, {int? before}) async {
  final res = await dio.get(
    '/chat/conversations/$conversationId/messages/search/',
    queryParameters: {'q': q, if (before != null) 'before': before},
  );
  return MessageSearchPage.fromJson(res.data['data']);
}

Future<MessageSearchPage> searchAllMessages(Dio dio, String q, {int? before}) async {
  final res = await dio.get(
    '/chat/messages/search/',
    queryParameters: {'q': q, if (before != null) 'before': before},
  );
  return MessageSearchPage.fromJson(res.data['data']);
}

/// Load history so [messageId] is on screen.
Future<List<dynamic>> messagesAround(Dio dio, int conversationId, int messageId) async {
  final res = await dio.get(
    '/chat/conversations/$conversationId/messages/',
    queryParameters: {'around': messageId},
  );
  return res.data['data'] as List;
}
```

---

## Walkthrough

### In-chat

1. Open chat → `GET …/messages/` as usual.
2. User taps Search → local `TextField`.
3. Debounce 300 ms; if `q.length >= 2` call in-chat search.
4. Keep `results` (newest first). Show `1 / N`.
5. Up = older (`index + 1`), down = newer (`index - 1`), wrap around.
6. If the hit is not in the loaded list, `GET …/messages/?around={id}`, replace the list, then `Scrollable.ensureVisible`.
7. Enter = next match; Shift+Enter = previous (web convention).

### Global (inbox)

1. Inbox search field already filters chat **titles** locally.
2. Same query, debounce, `GET /chat/messages/search/?q=`.
3. Section **Messages** under the chat list.
4. On tap: open `chat.id` (use inbox conversation if you have it, else participants from `chat`) and jump with `around`.

Do not send search over WebSocket.

---

## UI checklist

- [ ] Min 2 characters; empty state vs “type more”
- [ ] Debounce so you don’t hit the API every key
- [ ] Highlight current match; don’t append it as a new bubble
- [ ] Global hits include sender + chat name + snippet
- [ ] Pagination via `before` if you show “load more”
- [ ] Privacy: `sender` / `chat.participants` are already redacted like other public users

---

## Manual test plan

1. Send “invoice 123” in chat A. In-chat search `inv` → 1 match; jump highlights it.
2. Same text in chat B. Inbox search `invoice` → both under **Messages**; tap opens the right chat.
3. Delete for me on a match → it disappears from your search only.
4. Query `a` (1 char) → empty results, no error.
5. Old message not in the latest 50 → `around` loads a window that includes it.

---

## Related files

| Area | Path |
|------|------|
| Service | `backend/apps/chat/services/message_search_service.py` |
| Repository | `MessageRepository.search_messages` / `get_messages_around` |
| In-chat | `GET /api/chat/conversations/{id}/messages/search/` |
| Global | `GET /api/chat/messages/search/` |
| Web in-chat | `frontend/src/components/ChatWindow.tsx` |
| Web inbox | `frontend/src/components/ChatList.tsx` |
| OpenAPI | http://localhost:9000/api/docs/ |
