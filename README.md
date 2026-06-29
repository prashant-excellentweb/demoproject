# ChatApp - WhatsApp Clone

A full-featured WhatsApp-like chat application with SMS OTP login, real-time messaging, status/stories, and profile management.

## Features

- **SMS OTP Login** — Phone number authentication via Twilio (or console OTP in dev mode)
- **Real-time Chat** — WebSocket-powered instant messaging
- **Media Messages** — Send text, images, videos, PDFs, and documents
- **Status/Stories** — 24-hour expiring text, image, and video statuses
- **User Profiles** — Display name, about, avatar photo
- **Online Status** — See who's online and last seen
- **Read Receipts** — Message delivery and read indicators
- **Typing Indicators** — Real-time typing notifications
- **User Search** — Find contacts by name or phone number

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5, Django REST Framework, Channels |
| Real-time | WebSockets + Redis |
| Auth | JWT + SMS OTP (Twilio) |
| Frontend | React 18, TypeScript, Vite |
| Database | SQLite (dev) / PostgreSQL (prod) |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis (for WebSocket support)

### 1. Start Redis

```bash
# Docker
docker run -d -p 6379:6379 redis:alpine

# Or install Redis locally
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux

python manage.py migrate
python manage.py createsuperuser  # optional, use phone number
daphne -b 0.0.0.0 -p 9000 config.asgi:application
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

### Quick start (Windows PowerShell)

Open **two terminals** from project root `c:\Users\whtsappclone`:

**Terminal 1 — Backend (port 9000):**
```powershell
.\start-backend.ps1
```

**Terminal 2 — Frontend (port 5173):**
```powershell
.\start-frontend.ps1
```

> Backend uses **port 9000** (not 8000) so it won't conflict with your other project.

### 4. Login (Development)

1. Enter any phone number (e.g. `+1234567890`)
2. Click **Send OTP**
3. Check the **backend terminal** — the OTP is printed there
4. Enter the 6-digit code and login

## SMS Configuration (Production)

Add your Twilio credentials to `backend/.env`:

```env
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

Without Twilio credentials, OTP codes are printed to the server console.

## API Documentation (Flutter / Mobile)

| Resource | URL |
|----------|-----|
| Swagger UI | http://localhost:9000/api/docs/ |
| ReDoc | http://localhost:9000/api/redoc/ |
| OpenAPI JSON | http://localhost:9000/api/schema/ |
| Flutter guide | `backend/docs/FLUTTER_API.md` |
| OpenAPI YAML | `backend/docs/openapi.yaml` |

Regenerate schema after API changes:
```bash
python manage.py spectacular --file docs/openapi.yaml --validate
```

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/send-otp/` | Send OTP to phone |
| POST | `/api/auth/verify-otp/` | Verify OTP & get JWT |
| GET/PATCH | `/api/auth/profile/` | Get/update profile |
| GET | `/api/auth/search/?q=` | Search users |
| POST | `/api/auth/logout/` | Logout |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/chat/conversations/` | List conversations |
| POST | `/api/chat/conversations/direct/` | Start direct chat |
| POST | `/api/chat/conversations/group/` | Create group |
| GET | `/api/chat/conversations/{id}/messages/` | Get messages |
| POST | `/api/chat/conversations/{id}/send/` | Send message |
| POST | `/api/chat/conversations/{id}/read/` | Mark as read |

### Stories/Status
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stories/feed/` | Status feed |
| POST | `/api/stories/create/` | Create status |
| POST | `/api/stories/{id}/view/` | Mark viewed |
| DELETE | `/api/stories/{id}/delete/` | Delete status |

### WebSocket
```
ws://localhost:9000/ws/chat/?token=<JWT_ACCESS_TOKEN>
```

## Project Structure

```
whtsappclone/
├── backend/
│   ├── config/           # Django settings, ASGI, URLs
│   ├── apps/
│   │   ├── users/        # Auth, OTP, profiles
│   │   ├── chat/         # Messages, WebSockets
│   │   └── stories/      # Status/stories
│   └── manage.py
├── frontend/
│   └── src/
│       ├── components/   # UI components
│       ├── context/      # Auth & WebSocket
│       ├── pages/        # Login, Main app
│       └── api/          # API client
└── README.md
```

## Testing with Two Users

1. Open two browser windows (or one normal + one incognito)
2. Register two different phone numbers
3. Search for the other user and start a chat
4. Send messages, files, and create statuses

## License

MIT
