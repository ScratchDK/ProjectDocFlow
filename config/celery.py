from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

# Загрузка настроек из файла Django
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автоматическое обнаружение и регистрация задач из файлов tasks.py в приложениях Django
app.autodiscover_tasks()

# celery -A config purge    Очистить очередь
# celery -A config.celery worker --pool=solo -l INFO
# celery -A config.celery beat -l INFO
