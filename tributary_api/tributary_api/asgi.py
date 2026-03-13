"""
ASGI config for tributary_api project.
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tributary_api.settings.dev")

application = get_asgi_application()
