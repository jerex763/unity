"""High-value production configuration tests."""

import json
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_render_and_neon_production_settings_are_secure() -> None:
    script = """
import json
from django.conf import settings

database = settings.DATABASES["default"]
print(json.dumps({
    "allowed_hosts": settings.ALLOWED_HOSTS,
    "csrf_origins": settings.CSRF_TRUSTED_ORIGINS,
    "csrf_cookie_secure": settings.CSRF_COOKIE_SECURE,
    "session_cookie_secure": settings.SESSION_COOKIE_SECURE,
    "proxy_ssl_header": settings.SECURE_PROXY_SSL_HEADER,
    "database_engine": database["ENGINE"],
    "database_sslmode": database["OPTIONS"]["sslmode"],
    "server_side_cursors_disabled": database["DISABLE_SERVER_SIDE_CURSORS"],
}))
"""
    environment = os.environ.copy()
    environment.update(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings.prod",
            "DJANGO_SECRET_KEY": "test-production-secret",
            "DATABASE_URL": (
                "postgresql://unity:password@"
                "ep-example-pooler.ap-southeast-2.aws.neon.tech/unity"
            ),
            "RENDER_EXTERNAL_HOSTNAME": "unity-demo.onrender.com",
            "RENDER_EXTERNAL_URL": "https://unity-demo.onrender.com",
        }
    )
    environment.pop("DJANGO_ALLOWED_HOSTS", None)
    environment.pop("DJANGO_CSRF_TRUSTED_ORIGINS", None)

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND_DIR,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    configuration = json.loads(result.stdout)

    assert configuration == {
        "allowed_hosts": ["unity-demo.onrender.com"],
        "csrf_origins": ["https://unity-demo.onrender.com"],
        "csrf_cookie_secure": True,
        "session_cookie_secure": True,
        "proxy_ssl_header": ["HTTP_X_FORWARDED_PROTO", "https"],
        "database_engine": "django.db.backends.postgresql",
        "database_sslmode": "require",
        "server_side_cursors_disabled": True,
    }
