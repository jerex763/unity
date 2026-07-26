"""Production settings with fail-fast configuration validation."""

from urllib.parse import urlparse

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

if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Production DATABASE_URL must use PostgreSQL")

DATABASES["default"].setdefault("OPTIONS", {})["sslmode"] = env(
    "DJANGO_DATABASE_SSLMODE", default="require"
)
DATABASES["default"]["CONN_MAX_AGE"] = 0
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

render_hostname = env("RENDER_EXTERNAL_HOSTNAME", default="")
render_url = env("RENDER_EXTERNAL_URL", default="")
if render_hostname:
    parsed_hostname = urlparse(render_hostname)
    render_hostname = parsed_hostname.hostname or render_hostname

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
if render_hostname and render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_hostname)
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must be set in production")

CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
if render_url and render_url not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(render_url)

DEBUG = False
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=31_536_000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
