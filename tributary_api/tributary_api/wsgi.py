"""
WSGI config for tributary_api project.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tributary_api.settings.dev")

application = get_wsgi_application()
