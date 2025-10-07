import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
from api.payments.models import Installment
from api.purchases.models import Purchase
from api.users.models import CustomUser
from api.models import NotificationLog
from api.constants import NotificationCodes
from .utils import get_notification_by_code
from .tasks import send_email_task


logger = logging.getLogger(__name__)


@receiver(post_save, sender=Installment)
def send_installment_payment_notification(sender, instance, created, **kwargs):
    """Signal que envía notificación por email cuando una cuota cambia a estado PAID."""
    if settings.DISABLE_SIGNALS:
        logger.debug(
            "Signals deshabilitados - Saltando notificación de cuota pagada")
        return

    if created:
        return

    if instance.state != Installment.State.PAID:
        return

    notification_log = None

    try:
        template = get_notification_by_code(NotificationCodes.INSTALLMENT_PAID)

        user = instance.purchase.user
        user_email = user.email

        if not user_email:
            logger.warning(
                f"Usuario {user.id} no tiene email configurado. "
                f"No se puede enviar notificación de cuota pagada ID: {instance.id}"
            )
            return

        context_data = {
            'installment_id': instance.id,
            'installment_number': instance.num_installment,
            'purchase_id': instance.purchase.id,
            'amount_paid': str(instance.paid_amount) if instance.paid_amount else str(instance.amount_due),
            'amount_due': str(instance.amount_due),
            'installment_due_date': instance.due_date.isoformat(),
            'paid_at': instance.paid_at.isoformat() if instance.paid_at else timezone.now().isoformat(),
            'user_id': user.id,
            'user_email': user_email,
            'user_full_name': user.full_name()
        }

        try:
            notification_log = NotificationLog.objects.create(
                user=user,
                template=template,
                context_json=context_data,
                recipient_email=user_email,
                status=NotificationLog.Status.PENDING
            )
        except Exception as log_create_error:
            logger.warning(
                f"Error creando NotificationLog: {str(log_create_error)}")

        send_email_task.delay(  # type: ignore[attr-defined]
            email=user_email,
            template_id=template.id,
            context=context_data,
            log_email_id=notification_log.id if notification_log else None
        )
        logger.info(
            f"Tarea de email encolada. Usuario: {user.id}, "
            f"Cuota: {instance.id}, Log: {notification_log.id}"
        )

    except Exception as e:
        error_message = f"Error enviando notificación de cuota pagada: {str(e)}"

        logger.error(
            f"Error enviando notificación de cuota pagada. "
            f"Usuario: {instance.purchase.user.id}, "
            f"Cuota: {instance.id}, "
            f"Error: {error_message}"
        )


@receiver(post_save, sender=Installment)
def send_installment_overdue_notification(sender, instance, created, **kwargs):
    """
    Signal que envía notificación por email cuando una cuota cambia a estado OVERDUE.

    Este signal se activa después de guardar una instancia de Installment.
    Solo procesa actualizaciones (no creaciones) donde el estado cambie a 'OVERDUE'.
    Notifica al usuario que tiene una cuota vencida/adeudada pendiente de pago.

    Args:
        sender: La clase del modelo que envió el signal (Installment)
        instance (Installment): La instancia de la cuota que fue guardada
        created (bool): True si el objeto fue creado, False si fue actualizado
        **kwargs: Argumentos adicionales del signal

    Returns:
        None

    Raises:
        Ninguna excepción es propagada - se registran los errores en logs

    Nota:
        - Solo procesa cuotas actualizadas (no creadas) que cambien a estado OVERDUE
        - Registra todas las acciones en NotificationLog para auditoría
        - Usa el template 'overdue_notice' para el contenido del email
        - Incluye información de la fecha de vencimiento y monto adeudado
        - En caso de error, registra el problema pero no interrumpe el flujo

    Contexto del email:
        - installment_id: ID de la cuota vencida
        - installment_number: Número de la cuota
        - purchase_id: ID de la compra asociada
        - amount_due: Monto adeudado
        - installment_due_date: Fecha original de vencimiento
        - installment_state: Estado actual (OVERDUE)
        - user_id: ID del usuario deudor
    """
    if settings.DISABLE_SIGNALS:
        logger.debug(
            "Signals deshabilitados - Saltando notificación de cuota vencida")
        return

    # Solo procesar actualizaciones, no creaciones
    if created:
        return

    # Solo procesar si el estado actual es OVERDUE
    if instance.state != Installment.State.OVERDUE:
        return

    notification_log = None

    try:
        # Verificar que el template de notificación existe y está activo
        template = get_notification_by_code(NotificationCodes.OVERDUE_NOTICE)

        user = instance.purchase.user
        user_email = user.email

        if not user_email:
            logger.warning(
                f"Usuario {user.id} no tiene email configurado. "
                f"No se puede enviar notificación de cuota adeudada ID: {instance.id}"
            )
            return

        # Crear contexto para el log de notificación
        context_data = {
            'installment_id': instance.id,
            'installment_number': instance.num_installment,
            'purchase_id': instance.purchase.id,
            'amount_due': str(instance.amount_due),
            'user_id': user.id,
            'installment_due_date': instance.due_date.isoformat(),
            'installment_state': instance.state,
            "user_full_name": user.full_name()
        }

        try:
            notification_log = NotificationLog.objects.create(
                user=user,
                template=template,
                context_json=context_data,
                recipient_email=user_email,
                status=NotificationLog.Status.PENDING
            )
        except Exception as log_create_error:
            logger.warning(
                f"Error creando NotificationLog: {str(log_create_error)}")

        # Intentar enviar el email
        # Intentar enviar el email
        send_email_task.delay(  # type: ignore[attr-defined]
            email=user_email,
            template_id=template.id,
            context=context_data,
            log_email_id=notification_log.id if notification_log else None
        )

        logger.info(
            f"Notificación de cuota adeudada enviada exitosamente. "
            f"Usuario: {user.id}, Cuota: {instance.id}, Email: {user_email}"
        )

    except Exception as e:
        error_message = f"Error enviando notificación de cuota adeudada: {str(e)}"

        logger.error(
            f"Error enviando notificación de cuota adeudada. "
            f"Usuario: {instance.purchase.user.id}, "
            f"Cuota: {instance.id}, "
            f"Error: {error_message}"
        )


@receiver(post_save, sender=Purchase)
def send_purchase_confirmed_notification(sender, instance, created, **kwargs):
    """
    Signal que envía notificación por email cuando se confirma una compra.

    Este signal se activa después de crear una instancia de Purchase.
    Solo procesa creaciones nuevas (created=True) para notificar la confirmación
    de la compra al usuario que la realizó.

    Args:
        sender: La clase del modelo que envió el signal (Purchase)
        instance (Purchase): La instancia de la compra que fue creada
        created (bool): True si el objeto fue creado, False si fue actualizado
        **kwargs: Argumentos adicionales del signal

    Returns:
        None

    Raises:
        Ninguna excepción es propagada - se registran los errores en logs

    Nota:
        - Solo procesa compras nuevas (created=True)
        - Registra todas las acciones en NotificationLog para auditoría
        - Usa el template 'purchase_confirmed' para el contenido del email
        - Incluye información de la compra, productos y datos del usuario
        - En caso de error, registra el problema pero no interrumpe el flujo

    Contexto del email:
        - purchase_id: ID de la compra confirmada
        - purchase_date: Fecha de la compra
        - user_id: ID del usuario comprador
        - user_full_name: Nombre completo del usuario
    """
    if settings.DISABLE_SIGNALS:
        logger.debug(
            "Signals deshabilitados - Saltando notificación de compra confirmada")
        return

    # Solo procesar creaciones, no actualizaciones
    if not created:
        return

    notification_log = None

    try:
        # Verificar que el template de notificación existe y está activo
        template = get_notification_by_code(
            NotificationCodes.PURCHASE_CONFIRMED)

        user = instance.user
        user_email = user.email

        if not user_email:
            logger.warning(
                f"Usuario {user.id} no tiene email configurado. "
                f"No se puede enviar notificación de compra confirmada ID: {instance.id}"
            )
            return

        # Crear contexto para el log de notificación
        context_data = {
            'purchase_id': instance.id,
            'purchase_date': instance.purchase_date.isoformat(),
            'user_id': user.id,
            'user_full_name': user.full_name()
        }

        try:
            notification_log = NotificationLog.objects.create(
                user=user,
                template=template,
                context_json=context_data,
                recipient_email=user_email,
                status=NotificationLog.Status.PENDING
            )
        except Exception as log_create_error:
            logger.warning(
                f"Error creando NotificationLog: {str(log_create_error)}")

        # Intentar enviar el email
        send_email_task.delay(  # type: ignore[attr-defined]
            email=user_email,
            template_id=template.id,
            context=context_data,
            log_email_id=notification_log.id if notification_log else None
        )

        logger.info(
            f"Notificación de compra confirmada enviada exitosamente. "
            f"Usuario: {user.id}, Compra: {instance.id}, Email: {user_email}"
        )

    except Exception as e:
        error_message = f"Error enviando notificación de compra confirmada: {str(e)}"

        logger.error(
            f"Error enviando notificación de compra confirmada. "
            f"Usuario: {instance.user.id}, "
            f"Compra: {instance.id}, "
            f"Error: {error_message}"
        )


@receiver(post_save, sender=CustomUser)
def send_account_created_notification(sender, instance, created, **kwargs):
    """
    Signal que envía notificación por email cuando se crea una nueva cuenta de usuario.

    Este signal se activa después de crear una instancia de CustomUser.
    Solo procesa creaciones nuevas (created=True) para enviar el email de bienvenida
    al nuevo usuario registrado en el sistema.

    Args:
        sender: La clase del modelo que envió el signal (CustomUser)
        instance (CustomUser): La instancia del usuario que fue creado
        created (bool): True si el objeto fue creado, False si fue actualizado
        **kwargs: Argumentos adicionales del signal

    Returns:
        None

    Raises:
        Ninguna excepción es propagada - se registran los errores en logs

    Nota:
        - Solo procesa usuarios nuevos (created=True)
        - Registra todas las acciones en NotificationLog para auditoría
        - Usa el template 'created_account' para el contenido del email
        - Incluye información básica de la cuenta creada
        - En caso de error, registra el problema pero no interrumpe el flujo

    Contexto del email:
        - user_id: ID del usuario creado
        - username: Nombre de usuario
        - email: Email del usuario
        - user_full_name: Nombre completo del usuario
    """
    if settings.DISABLE_SIGNALS:
        logger.debug(
            "Signals deshabilitados - Saltando notificación de cuenta creada")
        return

    # Solo procesar creaciones, no actualizaciones
    if not created:
        return

    notification_log = None

    try:
        # Verificar que el template de notificación existe y está activo
        template = get_notification_by_code(NotificationCodes.CREATED_ACCOUNT)

        user_email = instance.email

        if not user_email:
            logger.warning(
                f"Usuario {instance.id} no tiene email configurado. "
                f"No se puede enviar notificación de cuenta creada ID: {instance.id}"
            )
            return

        # Crear contexto para el log de notificación
        context_data = {
            'user_id': instance.id,
            'username': instance.username,
            'email': instance.email,
            'user_full_name': instance.full_name()
        }

        try:
            notification_log = NotificationLog.objects.create(
                user=instance,
                template=template,
                context_json=context_data,
                recipient_email=user_email,
                status=NotificationLog.Status.PENDING
            )
        except Exception as log_create_error:
            logger.warning(
                f"Error creando NotificationLog: {str(log_create_error)}")

        # Intentar enviar el email
        send_email_task.delay(  # type: ignore[attr-defined]
            email=user_email,
            template_id=template.id,
            context=context_data,
            log_email_id=notification_log.id if notification_log else None
        )
        logger.info(
            f"Notificación de cuenta creada enviada exitosamente. "
            f"Usuario: {instance.id}, Email: {user_email}"
        )

    except Exception as e:
        error_message = f"Error enviando notificación de cuenta creada: {str(e)}"
        logger.error(
            f"Error enviando notificación de cuenta creada. "
            f"Usuario: {instance.id}, "
            f"Error: {error_message}"
        )


@receiver(post_save, sender=CustomUser)
def send_account_updated_notification(sender, instance, created, **kwargs):
    """
    Signal que envía notificación por email cuando se actualiza información de una cuenta de usuario.

    Este signal se activa después de guardar una instancia de CustomUser.
    Solo procesa actualizaciones (created=False) para notificar cambios en la cuenta
    del usuario. Se envía cuando se modifican datos importantes del perfil.

    Args:
        sender: La clase del modelo que envió el signal (CustomUser)
        instance (CustomUser): La instancia del usuario que fue actualizado
        created (bool): True si el objeto fue creado, False si fue actualizado
        **kwargs: Argumentos adicionales del signal

    Returns:
        None

    Raises:
        Ninguna excepción es propagada - se registran los errores en logs

    Nota:
        - Solo procesa usuarios actualizados (created=False)
        - Registra todas las acciones en NotificationLog para auditoría
        - Usa el template 'updated_account' para el contenido del email
        - Incluye información actualizada de la cuenta
        - En caso de error, registra el problema pero no interrumpe el flujo
        - Se recomienda agregar lógica para detectar cambios específicos importantes

    Contexto del email:
        - user_id: ID del usuario actualizado
        - username: Nombre de usuario actual
        - email: Email actual del usuario
        - user_full_name: Nombre completo actual del usuario
    """
    if settings.DISABLE_SIGNALS:
        logger.debug(
            "Signals deshabilitados - Saltando notificación de cuenta actualizada")
        return

    # Solo procesar actualizaciones, no creaciones
    if created:
        return

    notification_log = None

    try:
        # Verificar que el template de notificación existe y está activo
        template = get_notification_by_code(NotificationCodes.UPDATED_ACCOUNT)

        user_email = instance.email

        if not user_email:
            logger.warning(
                f"Usuario {instance.id} no tiene email configurado. "
                f"No se puede enviar notificación de cuenta actualizada ID: {instance.id}"
            )
            return

        # Crear contexto para el log de notificación
        context_data = {
            'user_id': instance.id,
            'username': instance.username,
            'email': instance.email,
            'user_full_name': instance.full_name()
        }

        try:
            notification_log = NotificationLog.objects.create(
                user=instance,
                template=template,
                context_json=context_data,
                recipient_email=user_email,
                status=NotificationLog.Status.PENDING
            )
        except Exception as log_create_error:
            logger.warning(
                f"Error creando NotificationLog: {str(log_create_error)}")

        # Intentar enviar el email
        send_email_task.delay(  # type: ignore[attr-defined]
            email=user_email,
            template_id=template.id,
            context=context_data,
            log_email_id=notification_log.id if notification_log else None
        )

        logger.info(
            f"Notificación de cuenta actualizada enviada exitosamente. "
            f"Usuario: {instance.id}, Email: {user_email}"
        )

    except Exception as e:
        error_message = f"Error enviando notificación de cuenta actualizada: {str(e)}"

        logger.error(
            f"Error enviando notificación de cuenta actualizada. "
            f"Usuario: {instance.id}, "
            f"Error: {error_message}"
        )


def send_payment_error_notification(installment, error_details: str):
    """
    Función auxiliar que envía notificación por email cuando ocurre un error en el pago de una cuota.

    Esta función no es un signal tradicional sino una utilidad que debe ser llamada
    manualmente cuando se detecta un error en el procesamiento de pagos de cuotas.
    Notifica al usuario sobre el problema y proporciona información para que pueda
    solucionarlo.

    Args:
        installment (Installment): La instancia de la cuota donde ocurrió el error
        error_details (str): Descripción detallada del error ocurrido

    Returns:
        None

    Raises:
        Ninguna excepción es propagada - se registran los errores en logs

    Nota:
        - Registra todas las acciones en NotificationLog para auditoría
        - Usa el template 'payment_error' para el contenido del email
        - Incluye información de la cuota y detalles del error
        - En caso de error al enviar, registra el problema pero no interrumpe el flujo
        - Esta función debe llamarse desde los servicios de pago cuando se detecte un error

    Contexto del email:
        - installment_id: ID de la cuota con error
        - installment_number: Número de la cuota
        - purchase_id: ID de la compra asociada
        - amount_due: Monto a pagar de la cuota
        - installment_due_date: Fecha de vencimiento de la cuota
        - user_id: ID del usuario afectado
        - user_full_name: Nombre completo del usuario
        - error_message: Descripción del error ocurrido

    Ejemplo de uso:
        from api.signals import send_payment_error_notification

        try:
            # lógica de procesamiento de pago
            process_payment(installment)
        except Exception as e:
            send_payment_error_notification(installment, str(e))
    """
    if settings.DISABLE_SIGNALS:
        logger.debug(
            "Signals deshabilitados - Saltando notificación de error de pago")
        return

    notification_log = None

    try:
        # Verificar que el template de notificación existe y está activo
        template = get_notification_by_code(NotificationCodes.PAYMENT_ERROR)

        user = installment.purchase.user
        user_email = user.email

        if not user_email:
            logger.warning(
                f"Usuario {user.id} no tiene email configurado. "
                f"No se puede enviar notificación de error de pago para cuota ID: {installment.id}"
            )
            return

        # Crear contexto para el log de notificación
        context_data = {
            'installment_id': installment.id,
            'installment_number': installment.num_installment,
            'purchase_id': installment.purchase.id,
            'amount_due': str(installment.amount_due),
            'installment_due_date': installment.due_date.isoformat(),
            'user_id': user.id,
            'user_full_name': user.full_name(),
            'error_message': error_details
        }

        try:
            notification_log = NotificationLog.objects.create(
                user=user,
                template=template,
                context_json=context_data,
                recipient_email=user_email,
                status=NotificationLog.Status.PENDING
            )
        except Exception as log_create_error:
            logger.warning(
                f"Error creando NotificationLog: {str(log_create_error)}")

        # Intentar enviar el email
        send_email_task.delay(  # type: ignore[attr-defined]
            email=user_email,
            template_id=template.id,
            context=context_data,
            log_email_id=notification_log.id if notification_log else None
        )
        logger.info(
            f"Notificación de error de pago enviada exitosamente. "
            f"Usuario: {user.id}, Cuota: {installment.id}, Email: {user_email}"
        )

    except Exception as e:
        error_message = f"Error enviando notificación de error de pago: {str(e)}"

        logger.error(
            f"Error enviando notificación de error de pago. "
            f"Usuario: {installment.purchase.user.id}, "
            f"Cuota: {installment.id}, "
            f"Error: {error_message}"
        )


def send_installment_due_7d_notification(installment):
    """Función auxiliar que envía recordatorio por email cuando una cuota vence en 7 días."""
    if settings.DISABLE_SIGNALS:
        logger.debug(
            "Signals deshabilitados - Saltando recordatorio de cuota próxima a vencer")
        return

    notification_log = None

    try:
        template = get_notification_by_code(
            NotificationCodes.INSTALLMENT_DUE_7D)

        user = installment.purchase.user
        user_email = user.email

        if not user_email:
            logger.warning(
                f"Usuario {user.id} no tiene email configurado. "
                f"No se puede enviar recordatorio de cuota próxima a vencer ID: {installment.id}"
            )
            return

        context_data = {
            'installment_id': installment.id,
            'installment_number': installment.num_installment,
            'purchase_id': installment.purchase.id,
            'amount_due': str(installment.amount_due),
            'installment_due_date': installment.due_date.isoformat(),
            'user_id': user.id,
            'user_full_name': user.full_name()
        }

        try:
            notification_log = NotificationLog.objects.create(
                user=user,
                template=template,
                context_json=context_data,
                recipient_email=user_email,
                status=NotificationLog.Status.PENDING
            )
        except Exception as log_create_error:
            logger.warning(
                f"Error creando NotificationLog: {str(log_create_error)}")

        send_email_task.delay(  # type: ignore[attr-defined]
            email=user_email,
            template_id=template.id,
            context=context_data,
            log_email_id=notification_log.id if notification_log else None
        )
        logger.info(
            f"Recordatorio de cuota próxima a vencer encolado. "
            f"Usuario: {user.id}, Cuota: {installment.id}, Email: {user_email}"
        )

    except Exception as e:
        error_message = f"Error enviando recordatorio de cuota próxima a vencer: {str(e)}"

        logger.error(
            f"Error enviando recordatorio de cuota próxima a vencer. "
            f"Usuario: {installment.purchase.user.id}, "
            f"Cuota: {installment.id}, "
            f"Error: {error_message}"
        )
