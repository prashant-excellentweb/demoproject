# ChatApp — Flutter Group Mentions & Admins-Only Messaging

Two group-only features:

1. **@mentions** (`@name`, `@everyone`) on send
2. **Only admins can message** — members can still read, react, and search

Replies and forward already work in groups the same as 1:1. See [`FLUTTER_REPLY_FORWARD_DRAFT.md`](./FLUTTER_REPLY_FORWARD_DRAFT.md). Use this with [`FLUTTER_API.md`](./FLUTTER_API.md) and [`FLUTTER_CHAT.md`](./FLUTTER_CHAT.md).

Sending is **REST only**. Live bubbles arrive on WebSocket `message` with `mentions` / `mentioned_me` / `mention_everyone`.

---

## What to build in Flutter

| Screen / area | Behavior |
|---------------|----------|
| **Group composer** | Typing `@` opens a member picker; include `@everyone` |
| **Send** | Multipart fields `mentioned_user_ids` and/or `mention_everyone` |
| **Bubble** | Color `@Name` tokens; highlight the row when `mentioned_me` |
| **Group info (admin)** | Toggle **Only admins can send messages** |
| **Group composer (member)** | If `admins_only_messages`, hide send / reply / forward / attach |
| **Forward picker** | Disable groups where you cannot post |

Mentions are ignored on 1:1 chats. Forwards do **not** copy mentions.

---

## API summary

| Method | Endpoint | Role |
|--------|----------|------|
| `POST` | `/chat/conversations/{id}/send/` | Optional `mentioned_user_ids`, `mention_everyone` |
| `PATCH` | `/chat/conversations/{id}/group/` | Admin: `admins_only_messages` (JSON or multipart) |
| `POST` | `/chat/conversations/{id}/messages/{id}/forward/` | Fails per target if that group is admins-only and you are not admin |

`created_by` is the group admin (`is_admin: true` on the conversation).

### Send with mentions (multipart)

```http
POST /chat/conversations/3/send/
Content-Type: multipart/form-data

content=Hey @Priya can you take this?
message_type=text
mentioned_user_ids=2
mention_everyone=false
```

`mentioned_user_ids` accepts a comma list (`2,5`) or a JSON array (`[2,5]`). Max **20** mentions.

`@everyone` / `@all` in the text also sets everyone-mode even if the flag is omitted.

Invalid IDs and non-members are dropped. Mentions in 1:1 are stored as none.

Non-admin send while `admins_only_messages` is on → **403** `"Only admins can send messages in this group."`

### Conversation fields

Every conversation payload includes:

```json
{
  "is_group": true,
  "is_admin": true,
  "created_by": 1,
  "admins_only_messages": false
}
```

### Message fields

```json
{
  "mention_everyone": false,
  "mentions": [{ "id": 2, "display_name": "Priya" }],
  "mentioned_me": true
}
```

Deleted-for-everyone messages clear these (`mentions: []`, `mentioned_me: false`).

---

## Dio

```dart
Future<Map<String, dynamic>> sendGroupText(
  Dio dio,
  int conversationId,
  String content, {
  int? replyToId,
  List<int> mentionedUserIds = const [],
  bool mentionEveryone = false,
}) async {
  final form = FormData.fromMap({
    'content': content,
    'message_type': 'text',
    if (replyToId != null) 'reply_to_id': replyToId,
    if (mentionedUserIds.isNotEmpty) 'mentioned_user_ids': mentionedUserIds.join(','),
    if (mentionEveryone) 'mention_everyone': true,
  });
  final res = await dio.post('/chat/conversations/$conversationId/send/', data: form);
  return res.data['data'] as Map<String, dynamic>;
}

Future<Map<String, dynamic>> setAdminsOnlyMessages(
  Dio dio,
  int conversationId, {
  required bool enabled,
}) async {
  final res = await dio.patch(
    '/chat/conversations/$conversationId/group/',
    data: {'admins_only_messages': enabled},
  );
  return res.data['data'] as Map<String, dynamic>;
}

bool canPostInGroup(Map<String, dynamic> conversation) {
  if (conversation['is_group'] != true) return true;
  if (conversation['admins_only_messages'] != true) return true;
  return conversation['is_admin'] == true;
}
```

Parse on `ChatMessage`:

```dart
final bool mentionEveryone;
final List<MentionUser> mentions;
final bool mentionedMe;

mentionEveryone: j['mention_everyone'] == true,
mentions: (j['mentions'] as List? ?? [])
    .map((e) => MentionUser.fromJson(e as Map<String, dynamic>))
    .toList(),
mentionedMe: j['mentioned_me'] == true,
```

And on `Conversation`: `adminsOnlyMessages: j['admins_only_messages'] == true`.

---

## Walkthrough

### Mentions

1. Group chat only. On `@` (start of word), show members minus self, plus **@everyone**.
2. Filter by `display_name` / phone as the user types.
3. Insert `@DisplayName ` (or `@everyone `) and keep the selected user IDs.
4. Send IDs + content. The server also parses `@FirstName` / `@everyone` from the text.
5. Render `@` tokens in teal. If `mentioned_me`, add a left accent on the incoming bubble.
6. Incoming WS `message` already includes mention fields — replace/dedupe by `id`.

Names with spaces: send **IDs**. The text parser only matches a token up to the next space.

### Admins-only mode

1. Admin opens Group info → toggle `PATCH …/group/` with `{ "admins_only_messages": true }`.
2. Refresh the conversation (or use `data` from the response).
3. Members: hide composer, reply, forward, and attach. Keep history, search, and reactions.
4. Header subtitle can show “Only admins can send messages”.
5. Forward into that group as a member → skip/disable that target; API returns a per-target error.

Admins can still reply and forward as usual.

---

## UI checklist

- [ ] `@` picker only in groups
- [ ] `@everyone` / `@all` marks everyone (`mention_everyone`)
- [ ] Incoming `mentioned_me` highlight
- [ ] Non-admin composer lock when `admins_only_messages`
- [ ] Admin toggle in group info
- [ ] Forward picker disables locked groups
- [ ] 403 copy: “Only admins can send messages in this group.”

---

## Manual test plan

1. Group of 3. Type `@Pr` → pick Priya → send. Priya’s client has `mentioned_me: true`; others see the `@Priya` token.
2. Send `@everyone lunch?` with no IDs → `mention_everyone: true`, every other member gets `mentioned_me`.
3. Admin enables **Only admins can send messages**. Member composer locks; admin can still send.
4. Member tries REST send anyway → 403.
5. Member forwards into that group → that target fails; other chats still succeed.
6. 1:1 `@Priya` is just plain text (no mention records).

---

## Related files

| Area | Path |
|------|------|
| Service | `backend/apps/chat/services/mention_service.py` |
| Models | `Conversation.admins_only_messages`, `Message.mention_everyone`, `MessageMention` |
| Send | `POST /api/chat/conversations/{id}/send/` |
| Group settings | `PATCH /api/chat/conversations/{id}/group/` |
| Web composer / picker | `frontend/src/components/ChatWindow.tsx` |
| Web group toggle | `frontend/src/components/GroupInfoPanel.tsx` |
| OpenAPI | http://localhost:9000/api/docs/ |
