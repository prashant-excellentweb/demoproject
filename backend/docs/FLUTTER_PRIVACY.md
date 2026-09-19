# ChatApp — Flutter Privacy Guide

Privacy controls for **Profile photo**, **About**, **Last seen & online**, and **Status**.

Use this with [`FLUTTER_API.md`](./FLUTTER_API.md) (auth + all endpoints) and [`FLUTTER_CHAT.md`](./FLUTTER_CHAT.md) (chat + WebSocket).

---

## What to build in Flutter

| Screen / area | Behavior |
|---------------|----------|
| **Privacy settings** | Four pickers: Profile photo, About, Last seen, Status → `everyone` / `contacts` / `nobody` |
| **Chat header** | Hide last-seen line when `last_seen == null && is_online == false` |
| **Avatars** | `avatar_url == null` → initials (no photo or privacy) |
| **Contact about** | Empty `about` may mean privacy, not an error |
| **Status feed** | Trust `/stories/feed/`; handle `403` on view if privacy blocks |

---

## API summary

| Method | Endpoint | Notes |
|--------|----------|-------|
| `GET` | `/auth/profile/` | Own profile **includes** privacy fields |
| `PATCH` | `/auth/profile/` | Update privacy (JSON or multipart) |
| `GET` | `/auth/users/{id}/` | Public user — **redacted** fields |
| `GET` | `/stories/feed/` | Excludes authors with `status_privacy: nobody` |

### Allowed values

```
everyone | contacts | nobody
```

| Setting | Default |
|---------|---------|
| `profile_photo_privacy` | `everyone` |
| `about_privacy` | `everyone` |
| `last_seen_privacy` | `everyone` |
| `status_privacy` | `contacts` |

**Contacts** = users who share at least one conversation with you.

---

## Update privacy (Dio)

```dart
Future<Map<String, dynamic>> updatePrivacySettings(
  Dio dio, {
  String? profilePhotoPrivacy,
  String? aboutPrivacy,
  String? lastSeenPrivacy,
  String? statusPrivacy,
}) async {
  final body = <String, dynamic>{
    if (profilePhotoPrivacy != null) 'profile_photo_privacy': profilePhotoPrivacy,
    if (aboutPrivacy != null) 'about_privacy': aboutPrivacy,
    if (lastSeenPrivacy != null) 'last_seen_privacy': lastSeenPrivacy,
    if (statusPrivacy != null) 'status_privacy': statusPrivacy,
  };
  final res = await dio.patch('/auth/profile/', data: body);
  if (res.data['success'] != true) {
    throw Exception(res.data['message'] ?? 'Failed to update privacy');
  }
  return res.data['data'] as Map<String, dynamic>;
}
```

Example call:

```dart
await updatePrivacySettings(
  dio,
  profilePhotoPrivacy: 'contacts',
  aboutPrivacy: 'everyone',
  lastSeenPrivacy: 'nobody',
  statusPrivacy: 'contacts',
);
```

---

## Redaction contract (other users)

When viewing **someone else’s** user object (search, chat participant, message sender, user detail):

| If privacy denies | You receive |
|-------------------|-------------|
| Profile photo | `avatar_url: null` |
| About | `about: ""` |
| Last seen | `last_seen: null`, `is_online: false` |

Your **own** `GET /auth/profile/` always returns real values + privacy prefs.

---

## Suggested Dart enums & helpers

```dart
enum PrivacyVisibility {
  everyone,
  contacts,
  nobody;

  static PrivacyVisibility parse(String? raw, {PrivacyVisibility fallback = PrivacyVisibility.everyone}) {
    return PrivacyVisibility.values.firstWhere(
      (e) => e.name == raw,
      orElse: () => fallback,
    );
  }
}

/// Chat subtitle: empty string means “don’t show last seen” (privacy or unknown).
String formatLastSeen({required bool isOnline, DateTime? lastSeen}) {
  if (!isOnline && lastSeen == null) return '';
  if (isOnline) return 'online';
  return 'last seen ${_relative(lastSeen!)}';
}
```

---

## UI checklist

- [ ] Privacy page under Profile / Settings with four rows and three options each
- [ ] Persist via `PATCH /auth/profile/` and refresh local user cache
- [ ] Chat header: only show subtitle when `formatLastSeen` is non-empty (or “Blocked”)
- [ ] Avatar widget: null URL → initials circle
- [ ] Status list: no special client filter needed beyond feed API
- [ ] On `403` from `/stories/{id}/view/`, pop viewer and show a short snackbar

---

## Manual test plan

1. User A sets **Last seen** → Nobody; User B opens chat → no online/last-seen text.
2. User A sets **Profile photo** → Contacts; User B (no shared chat) searches A → initials only; after starting a chat → photo visible.
3. User A sets **About** → Nobody; User B’s contact info shows empty about.
4. User A sets **Status** → Nobody; User B’s status feed does not list A.
5. User A sets **Status** → Contacts; User B (shared conversation) sees A’s status.

---

## Related files (backend / web)

| Area | Path |
|------|------|
| Model fields | `backend/apps/users/models.py` |
| Redaction | `backend/apps/users/services/privacy_service.py` |
| Profile PATCH | `PATCH /api/auth/profile/` |
| Web UI | `frontend/src/components/ProfilePanel.tsx` |
| OpenAPI | http://localhost:9000/api/docs/ |
