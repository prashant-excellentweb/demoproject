# Frontend / Mobile API notes

This app’s REST + WebSocket contract is documented for Flutter and web clients here:

- **Flutter guide (payloads, examples):** [`../backend/docs/FLUTTER_API.md`](../backend/docs/FLUTTER_API.md)
- **Swagger UI:** http://localhost:9000/api/docs/
- **OpenAPI YAML:** [`../backend/docs/openapi.yaml`](../backend/docs/openapi.yaml)

## Chat list filters

Tabs: **All** · **Unread** · **Favourites** · **Groups**

| Action | API |
|--------|-----|
| List with filter | `GET /chat/conversations/?filter=all\|unread\|groups\|favourites` |
| Toggle favourite | `POST /chat/conversations/{id}/favourite/` |

Conversation payload includes `is_favourite`. Favourites are sorted to the top in the All tab.

## Message delete (web + Flutter)

| Action | API | UI |
|--------|-----|----|
| Delete for me | `DELETE /chat/conversations/{id}/messages/{messageId}/` body `{ "delete_for": "me" }` | Message removed only from **your** chat |
| Delete for everyone | same URL, body `{ "delete_for": "everyone" }` | Everyone sees “This message was deleted” |

- **Delete for me:** any chat participant  
- **Delete for everyone:** message sender, or group admin  

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
