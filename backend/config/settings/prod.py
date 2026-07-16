"""Production settings with fail-fast configuration validation."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import env


def required_setting(name: str) -> str:
    """Return a non-empty environment setting or fail during startup."""
    value = env(name, default="")
    if not value:
        raise ImproperlyConfigured(f"{name} must be set in production")
    return value


SECRET_KEY = required_setting("DJANGO_SECRET_KEY")
DATABASES = {"default": env.db("DATABASE_URL")}
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be set in production")

DEBUG = False
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=31_536_000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
