"""
Development settings for TRIBUTARY API.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Use console email backend for local development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Allow SQLite for optional local dev only
# But default is still PostgreSQL as per spec
import dj_database_url  # noqa: E402
import os  # noqa: E402

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    DATABASES["default"] = dj_database_url.parse(DATABASE_URL)  # noqa: F405
