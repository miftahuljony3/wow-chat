"""
Wow Chat – Django Settings
Tagline: An intelligent assistant by JONY
"""

import environ
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# ── Application Definition ────────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "channels",
    "django_celery_beat",
    "django_celery_results",
    "django_filters",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.channels_integration",
    "apps.inbox",
    "apps.webhooks",
    "apps.ai_agent",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

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

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

# ── Databases ─────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="wowchat"),
        "USER": env("POSTGRES_USER", default="wowchat"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="wowchat_secret"),
        "HOST": env("POSTGRES_HOST", default="postgres"),
        "PORT": env("POSTGRES_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }
}

# MongoDB connection settings (used by MongoRepository classes)
MONGODB = {
    "HOST": env("MONGO_HOST", default="mongodb"),
    "PORT": env.int("MONGO_PORT", default=27017),
    "USER": env("MONGO_USER", default="wowchat"),
    "PASSWORD": env("MONGO_PASSWORD", default="wowchat_secret"),
    "DB": env("MONGO_DB", default="wowchat_messages"),
}

MONGO_URI = (
    f"mongodb://{MONGODB['USER']}:{MONGODB['PASSWORD']}"
    f"@{MONGODB['HOST']}:{MONGODB['PORT']}/{MONGODB['DB']}"
    f"?authSource=admin"
)

# ── Caching (Redis) ───────────────────────────────────────────────────────────
_REDIS_URL = (
    f"redis://:{env('REDIS_PASSWORD', default='wowchat_redis')}"
    f"@{env('REDIS_HOST', default='redis')}"
    f":{env('REDIS_PORT', default='6379')}"
)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"{_REDIS_URL}/1",
    }
}

# ── Channels (WebSocket) ──────────────────────────────────────────────────────
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [f"{_REDIS_URL}/2"],
            "capacity": 1500,
            "expiry": 10,
        },
    }
}

# ── Celery ────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=f"{_REDIS_URL}/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="django-db")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes hard limit per task
CELERY_TASK_SOFT_TIME_LIMIT = 240

CELERY_TASK_QUEUES_DEFAULT = "default"
CELERY_TASK_ROUTES = {
    "apps.webhooks.tasks.*": {"queue": "webhooks"},
    "apps.ai_agent.tasks.*": {"queue": "ai_responses"},
}

# ── Django REST Framework ─────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "2000/hour",
        "webhook": "10000/hour",  # webhooks need high limits
    },
}

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"]
)
CORS_ALLOW_CREDENTIALS = True

# ── Auth ──────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Static & Media ────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ── Localisation ──────────────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── WhatsApp / Meta ───────────────────────────────────────────────────────────
WHATSAPP_VERIFY_TOKEN = env("WHATSAPP_VERIFY_TOKEN", default="")
WHATSAPP_APP_SECRET = env("WHATSAPP_APP_SECRET", default="")

# ── AI / LLM ─────────────────────────────────────────────────────────────────
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
OPENAI_MODEL = env("OPENAI_MODEL", default="gpt-4o-mini")

# ── App URLs ──────────────────────────────────────────────────────────────────
SITE_BASE_URL = env("SITE_BASE_URL", default="http://localhost:8000")
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")
