"""
Production settings for TRIBUTARY API.
"""
import os

import dj_database_url

from .base import *  # noqa: F401, F403

DEBUG = False

# Use os.environ directly — python-decouple may not see Render env vars
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")  # noqa: F405

# Database from Render environment
DATABASES["default"] = dj_database_url.config(  # noqa: F405
    default=config("DATABASE_URL"),  # noqa: F405
    conn_max_age=600,
    ssl_require=True,
)

# SendGrid email backend
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.sendgrid.net"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "apikey"
EMAIL_HOST_PASSWORD = config("SENDGRID_API_KEY")  # noqa: F405

# Security — Render terminates SSL at the load balancer
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = False  # Render handles SSL; enabling this causes redirect loops
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
