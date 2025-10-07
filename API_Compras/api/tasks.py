from celery import shared_task
from .services import sendEmail
from .models import NotificationTemplate
from .models import NotificationLog
from django.utils import timezone
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, name="send_email_task")
def send_email_task(self, email, template_id, context, log_email_id):
    log_email = None
    try:
        cache_key = f"notification_template_{template_id}"
        template = cache.get(cache_key)

        if not template:
            template = NotificationTemplate.objects.get(id=template_id)
            cache.set(cache_key, template, timeout=14400)  # 4 horas

        log_email = NotificationLog.objects.get(id=log_email_id)
        start_time = timezone.now()

        sendEmail(email, template, context)

        end_time = timezone.now()
        duration = end_time - start_time

        log_email.sent_at = timezone.now()
        log_email.save(update_fields=['sent_at'])
        log_email.status = NotificationLog.Status.SENT
        log_email.time_duration = duration.total_seconds()
        log_email.save()

    except Exception as exc:
        error_message = f"Error enviando notificación: {str(exc)}"
        if log_email is not None:
            try:
                log_email.status = NotificationLog.Status.ERROR
                log_email.error_message = error_message
                log_email.save(
                    update_fields=['status', 'error_message'])
            except Exception as log_error:
                logger.error(
                    f"Error actualizando log_email: {str(log_error)}")

        logger.error(
            f"Error enviando notificación. "
            f"Usuario: {context.get('user_id')}, "
            f"Error: {error_message}"
        )
        # Reintentar después de 60 segundos
        raise self.retry(exc=exc, countdown=60)
