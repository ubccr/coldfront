from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

# Imposta il modulo delle impostazioni Django per 'celery'.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldfront.config.settings')

app = Celery('coldfront')

# Carica le impostazioni di Celery dal file di configurazione di Django.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Scopri i task all'interno delle app installate.
app.autodiscover_tasks(['coldfront.core.periodic'])

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

# Configurazione di Celery Beat (se usato)
app.conf.beat_schedule = {
    'update-allocations-usage-every-10-minutes': {
        'task': 'coldfront.core.periodic.tasks.update_allocations_usage',
        'schedule': crontab(minute='*/10'),  # Ogni 10 minuti
    },
}
