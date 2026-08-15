"""Shared Django settings for Unity."""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, []),
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, []),
    PUBLIC_REGISTRATION_RATE_LIMIT=(int, 12),
    PUBLIC_REGISTRATION_TOKEN_RATE_LIMIT=(int, 120),
    PUBLIC_REGISTRATION_RATE_WINDOW_SECONDS=(int, 600),
    PUBLIC_REGISTRATION_TRUSTED_PROXY_HOPS=(int, 0),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-development-only-key")
DEBUG = env.bool("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS")

PRIVACY_NOTICE_VERSION = env(
    "PRIVACY_NOTICE_VERSION",
    default="2026-08-contact-methods-v1",
)
PRIVACY_NOTICE_TEXT = env(
    "PRIVACY_NOTICE_TEXT",
    default=(
        "Unity collects your name, contact details and event registration "
        "so the hosting church can administer this event and contact you about "
        "it. Authorized church workers and the services needed to operate Unity may "
        "access this information. It is not sold or used for commercial advertising. "
        "Contact the hosting church to access or correct your information, ask a "
        "privacy question, or withdraw consent for future handling."
    ),
)
PUBLIC_REGISTRATION_RATE_LIMIT = env.int("PUBLIC_REGISTRATION_RATE_LIMIT")
PUBLIC_REGISTRATION_TOKEN_RATE_LIMIT = env.int("PUBLIC_REGISTRATION_TOKEN_RATE_LIMIT")
PUBLIC_REGISTRATION_RATE_WINDOW_SECONDS = env.int(
    "PUBLIC_REGISTRATION_RATE_WINDOW_SECONDS"
)
PUBLIC_REGISTRATION_TRUSTED_PROXY_HOPS = env.int(
    "PUBLIC_REGISTRATION_TRUSTED_PROXY_HOPS"
)

INSTALLED_APPS = [
    "accounts.apps.AccountsConfig",
    "audit.apps.AuditConfig",
    "care.apps.CareConfig",
    "events.apps.EventsConfig",
    "groups.apps.GroupsConfig",
    "people.apps.PeopleConfig",
    "tenancy.apps.TenancyConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "audit.middleware.AuditRequestMiddleware",
    "tenancy.middleware.ActiveChurchMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "frontend_dist"],
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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgresql://unity:unity@localhost:5432/unity",
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        )
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-au"
TIME_ZONE = "Australia/Sydney"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
FRONTEND_DIST_DIR = BASE_DIR / "frontend_dist"
WHITENOISE_ROOT = FRONTEND_DIST_DIR
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}
