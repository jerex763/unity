"""Fast, isolated settings for automated tests."""

import os

import environ

from .base import *  # noqa: F403

SECRET_KEY = "test-only-secret-key"
DEBUG = False
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if TEST_DATABASE_URL:
    DATABASES = {
        "default": environ.Env.db_url_config(TEST_DATABASE_URL),
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Public, fixed fixture key; never use outside isolated tests.
PUBLIC_LINK_ENCRYPTION_KEYS = ["MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="]
