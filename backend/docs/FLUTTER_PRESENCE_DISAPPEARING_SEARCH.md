# Presence, Disappearing Messages, View Once, Global Search

Companion to [`FLUTTER_CHAT.md`](./FLUTTER_CHAT.md) and [`FLUTTER_MESSAGE_SEARCH.md`](./FLUTTER_MESSAGE_SEARCH.md).

---

## 1. Online / last seen (live presence)

WS connect sets `is_online=true`; disconnect sets `false` and updates `last_seen`.

Contacts receive:

```json
{ "type": "presence", "user_id": 2, "is_online": true, "last_seen": "2026-09-21T10:00:00Z" }
```

Privacy (`last_seen_privacy`) is applied per viewer before broadcast. If redacted: `is_online: false`, `last_seen: null`.

Update the open chat header and inbox avatars from this event (do not poll).

---

## 2. Disappearing messages (per chat)

| Duration | Value |
|----------|-------|
| Off | `off` |
| 24 hours | `24h` |
| 7 days | `7d` |
| 90 days | `90d` |

```http
PATCH /api/chat/conversations/{id}/disappearing/
{ "duration": "24h" }
```

Conversation includes `disappearing_messages`. New messages get `expires_at`; expired ones soft-delete for everyone (also purged when loading history).

WS: `conversation_updated` after a duration change.

---

## 3. View once media

Send image/video with multipart field `is_view_once=true`.

List/history: recipients get **no** `file_url` until they open.

```http
POST /api/chat/conversations/{id}/messages/{messageId}/view-once/
```

Response includes a **one-time** `file_url`, then media is cleared. Fields: `is_view_once`, `view_once_opened`, `view_once_opened_at`.

Broadcast: `message_updated`.

---

## 4. Global search (categorized)

```http
GET /api/chat/search/?q=invoice
```

```json
{
  "query": "invoice",
  "contacts": [ /* UserPublic */ ],
  "groups": [ /* chat summaries */ ],
  "messages": [ /* MessageSearchHit */ ],
  "media": [],
  "links": [],
  "docs": []
}
```

Min 2 characters. Existing `GET /chat/messages/search/` still works for messages only.

---

## 5. In-chat search (prev / next)

Unchanged: `GET …/messages/search/?q=` + up/down navigation + `?around=`.

---

## 6. Media filters (Photos / Videos / Links / Docs / Audio)

```http
GET /api/chat/conversations/{id}/media/?type=photos
```

`type`: `photos` | `videos` | `links` | `docs` | `audio`

```json
{ "type": "photos", "results": [ /* Message */ ], "has_more": false }
```

---

## Quick Dio

```dart
await dio.patch('/chat/conversations/$id/disappearing/', data: {'duration': '7d'});
form.fields.add(MapEntry('is_view_once', 'true'));
await dio.post('/chat/conversations/$id/messages/$mid/view-once/');
await dio.get('/chat/search/', queryParameters: {'q': q});
await dio.get('/chat/conversations/$id/media/', queryParameters: {'type': 'docs'});
```
