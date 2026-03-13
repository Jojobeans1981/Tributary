import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tributary_api.settings.dev")

app = Celery("tributary_api")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
