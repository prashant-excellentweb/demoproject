import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-key-change-in-production")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
# ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "apps.users",
    "apps.chat",
    "apps.stories",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    os.getenv("FRONTEND_URL", "http://localhost:5173"),
]
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.common.exception_handler.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=7),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
}

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

try:
    import redis

    redis.from_url(REDIS_URL).ping()
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }
except Exception:
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

OTP_EXPIRY_MINUTES = 5
STORY_EXPIRY_HOURS = 24

# Static OTP for dev/testing. Set STATIC_OTP= to empty string to use random OTP + Twilio.
STATIC_OTP = os.getenv("STATIC_OTP", "111111")

FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024

SPECTACULAR_SETTINGS = {
    "TITLE": "ChatApp API",
    "DESCRIPTION": """
WhatsApp-clone REST API for Flutter/mobile clients.

## Standard response format (all APIs)

Every endpoint returns the same JSON structure:

```json
{
  "success": true,
  "message": "Human readable message",
  "data": { }
}
```

On error:
```json
{
  "success": false,
  "message": "Error description",
  "data": null
}
```

Validation errors put field errors inside `data`.

## Authentication
1. `POST /api/auth/send-otp/` — send OTP to phone (no auth)
2. `POST /api/auth/verify-otp/` — verify OTP, receive JWT `access` + `refresh` tokens
3. Send header on all protected routes: `Authorization: Bearer <access_token>`
4. `POST /api/auth/token/refresh/` — refresh access token

## WebSocket (real-time chat)
- URL: `ws://<host>:9000/ws/chat/?token=<access_token>`
- Actions (JSON): `join_conversation`, `leave_conversation`, `typing`, `mark_read`
- Events received: `message`, `message_deleted`, `message_updated`, `typing`, `read`

## Message delete
- `DELETE /api/chat/conversations/{id}/messages/{message_id}/`
- Body: `{ "delete_for": "me" }` — hide only for current user
- Body: `{ "delete_for": "everyone" }` — soft-delete for all (sender or group admin)

## Reactions
- `POST /api/chat/conversations/{id}/messages/{message_id}/react/`
- Body: `{ "emoji": "👍" }` — allowed: 👍 ❤️ 😂 😮 😢 🙏 🔥 👏

## Media uploads
Use `multipart/form-data` for messages, profile avatar, and status media.
    """,
    "VERSION": "1.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/",
    "TAGS": [
        {"name": "Auth", "description": "SMS OTP login, profile, user search"},
        {"name": "Chat", "description": "Conversations and messages"},
        {"name": "Stories", "description": "Status/stories (24h expiry)"},
    ],
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayRequestDuration": True,
    },
}
