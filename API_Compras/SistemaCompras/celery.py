import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SistemaCompras.settings')

app = Celery('SistemaCompras')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Tarea de prueba para verificar que Celery funciona"""
    print(f'Request: {self.request!r}')
