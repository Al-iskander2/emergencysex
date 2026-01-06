import os
from pathlib import Path

from dotenv import load_dotenv

# -----------------------------
# Base configuration
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DEBUG = os.getenv("DJANGO_DEBUG", "False") == "True"

# SECRET_KEY: require in production, allow fallback in development
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-insecure-key-change-me"
    else:
        raise ValueError("DJANGO_SECRET_KEY must be set in production")

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "testserver",
]

render_external_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if render_external_hostname:
    ALLOWED_HOSTS.append(render_external_hostname)

# -----------------------------
# Applications
# -----------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Project apps
    "emerg_database",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "emerg_django.urls"

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
                "django.template.context_processors.static",
                "django.template.context_processors.media",
            ],
        },
    },
]

WSGI_APPLICATION = "emerg_django.wsgi.application"
ASGI_APPLICATION = "emerg_django.asgi.application"

# -----------------------------
# Database
# -----------------------------
if os.getenv("USE_SQLITE", "False") == "True":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "emeg"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 600,
            "OPTIONS": {"connect_timeout": 10},
        }
    }

# -----------------------------
# Auth
# -----------------------------
AUTH_USER_MODEL = "emerg_database.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/"

# -----------------------------
# I18N / TZ
# -----------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Dublin"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -----------------------------
# Static & media
# -----------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
RENDER = bool(os.getenv("RENDER"))
MEDIA_ROOT = "/tmp/media" if RENDER else (BASE_DIR / "media")

# -----------------------------
# Security hardening (basic)
# -----------------------------
CSRF_TRUSTED_ORIGINS = [o for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o]
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"
