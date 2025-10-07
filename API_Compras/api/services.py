import logging
from django.core.mail import send_mail
from django.http import HttpResponse
import os
from dotenv import load_dotenv
from .utils import get_notification_by_code
from api.models import NotificationLog
from api.constants import NotificationCodes
from django.utils import timezone
from api.payments.models import Installment
from .models import NotificationTemplate
from api.purchases.models import Purchase

logger = logging.getLogger(__name__)


def sendEmail(destination_email, template: NotificationTemplate, context: dict = {}):
    """
    Envía un correo usando Django email backend.

    Args:
        destination_email (str): Email de destino
        template (NotificationTemplate): Template de la notificación
        context (dict): Contexto para renderizar el mensaje

    Returns:
        HttpResponse: Respuesta indicando el estado del envío
    """
    try:
        load_dotenv()

        html_message = defined_message_html(template, context)

        send_mail(
            subject=template.subject,
            message='',
            from_email=os.getenv('EMAIL_HOST_USER'),
            recipient_list=[destination_email],
            fail_silently=False,
            html_message=html_message
        )

        return HttpResponse('Correo enviado con éxito')
    except Exception as e:
        logger.error(f"Error enviando el correo: {e}")
        raise


def defined_message_html(template: NotificationTemplate, context: dict) -> str:
    """
    Construye el HTML del email basado en el template y contexto.

    Args:
        template (NotificationTemplate): Template de la notificación
        context (dict): Contexto con variables dinámicas

    Returns:
        str: HTML renderizado del email

    Raises:
        ValueError: Si el template o contexto son inválidos
    """
    if not template or not isinstance(template, NotificationTemplate):
        raise ValueError(
            "Template must be a valid NotificationTemplate instance")
    if not context or not isinstance(context, dict):
        raise ValueError("Context must be a valid dictionary")

    head = template.head_html
    footer = template.footer_html
    header = f"<h1>{template.subject}</h1>"

    user_full_name_raw = context.get("user_full_name", "N/A")
    user_full_name = f" | {user_full_name_raw}" if user_full_name_raw != 'N/A' else ""

    purchase_id = context.get("purchase_id")
    purchase = None
    if purchase_id is not None:
        purchase = Purchase.objects.select_related().prefetch_related(
            'details__product'
        ).filter(id=purchase_id).first()

    installment_number = context.get("installment_number", "")
    amount_due = context.get("amount_due", "")
    installment_due_date = context.get("installment_due_date", "")
    surcharge_pct = context.get("surcharge_pct", "")
    total_with_surcharge = context.get("total_with_surcharge", "")
    username = context.get("username", "")
    email = context.get("email", "")
    error_message = context.get("error_message", "")
    purchase_date = context.get("purchase_date", "")

    if not purchase:
        total_installments = 0
        products_detail = ["<li>No se encontraron productos</li>"]
    else:
        total_installments = purchase.total_installments_count
        details = purchase.details.all()
        products_detail = []

        if details.exists():
            for detail in details:
                products_detail.append(
                    f"<li>{detail.quantity} x {detail.product.name}</li>"
                )
        else:
            products_detail = ["<li>No hay productos en esta compra</li>"]

    content = _build_email_content(
        template.code,
        user_full_name,
        installment_number,
        total_installments,
        amount_due,
        installment_due_date,
        surcharge_pct,
        total_with_surcharge,
        products_detail,
        purchase_id,
        purchase.total_amount if purchase else 'N/A',
        purchase_date,
        username,
        email,
        error_message
    )

    body = f"""
    <!DOCTYPE html>
    <html lang="es">
        {head}
        <body>
            <div class="header">
                {header}
            </div>
            <div class="content">
                {content}
            </div>
            {footer}
        </body>
    </html> 
    """
    return body


def _build_email_content(code, user_full_name, installment_number, total_installments,
                         amount_due, installment_due_date, surcharge_pct, total_with_surcharge,
                         products_detail, purchase_id, total_amount, purchase_date,
                         username, email, error_message):
    """
    Construye el contenido específico del email según el código de notificación.
    """
    if code == NotificationCodes.OVERDUE_NOTICE:
        return f"""
        <p>Estimado/a {user_full_name}</p>
        <p>Le informamos que su cuota con vencimiento el <strong>{installment_due_date}</strong> se encuentra <b>pendiente de pago.</b></p>
        
        <p>Detalles de la cuota:</p>
        <ul>
            <li>Número de cuota: <strong>#{installment_number}|{total_installments}</strong></li>
            <li>Monto adeudado: <strong>{amount_due}</strong></li>
            <li>Fecha de vencimiento: <strong>{installment_due_date}</strong></li>
        </ul>
        
        <p>Productos de la compra:</p>
        <ul>
            {''.join(products_detail)}
        </ul>
        
        <p>Le recordamos la importancia de mantener sus pagos al día para evitar recargos adicionales.</p> 
        """

    if code == NotificationCodes.OVERDUE_SURCHARGE_NOTICE:
        return f"""
        <p>Estimado/a {user_full_name}</p>
        <p>Le informamos que su cuota con vencimiento el <strong>{installment_due_date}</strong> se encuentra <b>pendiente de pago y ha generado un recargo del {surcharge_pct}%.</b></p>
        
        <p>Detalles de la cuota:</p>
        <ul>
            <li>Número de cuota: <strong>#{installment_number}|{total_installments}</strong></li>
            <li>Monto adeudado: <strong>{amount_due}</strong></li>
            <li>Recargo aplicado: <strong>{surcharge_pct}%</strong></li>
            <li>Total con recargo: <strong>{total_with_surcharge}</strong></li>
            <li>Fecha de vencimiento: <strong>{installment_due_date}</strong></li>
        </ul>
        
        <p>Productos de la compra:</p>
        <ul>
            {''.join(products_detail)}
        </ul>
        
        <p>Le recordamos la importancia de mantener sus pagos al día para evitar recargos adicionales.</p>
        <p>Pasado 7 días luego de <strong>{installment_due_date}</strong>, su cuota podría generar un recargo.</p>
        """

    if code == NotificationCodes.INSTALLMENT_DUE_7D:
        return f"""
        <p>Estimado/a {user_full_name}</p>
        <p>Le informamos que su cuota con vencimiento el <strong>{installment_due_date}</strong> se encuentra <b>pendiente de pago y vence en 7 días.</b></p>
        
        <p>Detalles de la cuota:</p>
        <ul>
            <li>Número de cuota: <strong>#{installment_number}|{total_installments}</strong></li>
            <li>Monto adeudado: <strong>{amount_due}</strong></li>
            <li>Fecha de vencimiento: <strong>{installment_due_date}</strong></li>
        </ul>
        
        <p>Productos de la compra:</p>
        <ul>
            {''.join(products_detail)}
        </ul>
        
        <p>Le recordamos la importancia de mantener sus pagos al día para evitar recargos adicionales.</p>
        <p>Pasado 7 días luego de <strong>{installment_due_date}</strong>, su cuota podría generar un recargo.</p>
        """

    if code == NotificationCodes.PURCHASE_CONFIRMED:
        return f"""
        <p>Estimado/a {user_full_name}</p>
        <p>Le confirmamos que su compra ha sido procesada exitosamente.</p>
        
        <p>Detalles de la compra:</p>
        <ul>
            <li>ID de la compra: <strong>{purchase_id}</strong></li>
            <li>Total de cuotas: <strong>{total_installments}</strong></li>
            <li>Monto total: <strong>{total_amount if total_amount != 'N/A' else 'No disponible'}</strong></li>
            <li>Fecha de compra: <strong>{purchase_date}</strong></li>
        </ul>
        
        <p>Productos de la compra:</p>
        <ul>
            {''.join(products_detail)}
        </ul>
        
        <p>Gracias por confiar en nosotros.</p>
        """

    if code == NotificationCodes.INSTALLMENT_PAID:
        return f"""
        <p>Estimado/a {user_full_name}</p>
        <p>Le confirmamos que hemos recibido el pago de su cuota.</p>
        
        <p>Detalles de la cuota pagada:</p>
        <ul>
            <li>Número de cuota: <strong>#{installment_number}|{total_installments}</strong></li>
            <li>Monto pagado: <strong>{amount_due}</strong></li>
            <li>Fecha de vencimiento: <strong>{installment_due_date}</strong></li>
        </ul>
        
        <p>Productos de la compra:</p>
        <ul>
            {''.join(products_detail)}
        </ul>
        
        <p>Gracias por mantener sus pagos al día.</p>
        """

    if code == NotificationCodes.CREATED_ACCOUNT:
        return f"""
        <p>Estimado/a {user_full_name}</p>
        <p>Le damos la bienvenida a nuestro sistema de compras. Su cuenta ha sido creada exitosamente.</p>
        
        <p>Detalles de su cuenta:</p>
        <ul>
            <li>Nombre de usuario: <strong>{username}</strong></li>
            <li>Email: <strong>{email}</strong></li>
        </ul>
        
        <p>Estamos encantados de tenerlo con nosotros.</p>
        """

    if code == NotificationCodes.PAYMENT_ERROR:
        return f"""
        <p>Estimado/a {user_full_name}</p>
        <p>Le informamos que ha ocurrido un error al procesar el pago de su cuota.</p>
        
        <p>Detalles del error:</p>
        <ul>
            <li>Número de cuota: <strong>#{installment_number}|{total_installments}</strong></li>
            <li>Monto: <strong>{amount_due}</strong></li>
            <li>Fecha de vencimiento: <strong>{installment_due_date}</strong></li>
            <li>Error: <strong>{error_message}</strong></li>
        </ul>
        
        <p>Por favor, intente realizar el pago nuevamente o contacte a soporte si el problema persiste.</p>
        """

    if code == NotificationCodes.UPDATED_ACCOUNT:
        return f"""
        <p>Estimado/a {user_full_name}</p>
        <p>Le informamos que los detalles de su cuenta han sido actualizados exitosamente.</p>
        
        <p>Detalles actualizados de su cuenta:</p>
        <ul>
            <li>Nombre de usuario: <strong>{username}</strong></li>
            <li>Email: <strong>{email}</strong></li>
        </ul>
        
        <p>Si usted no realizó estos cambios, por favor contacte a soporte inmediatamente.</p>
        """

    return "<p>Contenido no definido en el template.</p>"


def send_installment_mora_notification(installment: Installment):
    """
    Envía notificación de cuota con mora.

    IMPORTANTE: Esta función importa send_email_task dentro de la función
    para evitar imports circulares.
    """
    from django.conf import settings
    from .tasks import send_email_task

    if settings.DISABLE_SIGNALS:
        logger.debug(
            "Signals deshabilitados - Saltando notificación de cuota con mora")
        return

    notification_log = None

    try:
        template = get_notification_by_code(
            NotificationCodes.OVERDUE_SURCHARGE_NOTICE)

        user = installment.purchase.user
        user_email = user.email

        if not user_email:
            logger.warning(
                f"Usuario {user.id} no tiene email configurado. "
                f"No se puede enviar notificación de cuota adeudada por mora ID: {installment.pk}"
            )
            return

        context_data = {
            'installment_id': installment.pk,
            'installment_number': installment.num_installment,
            'purchase_id': installment.purchase.pk,
            'surcharge_pct': str(installment.surcharge_pct),
            'amount_due': str(installment.amount_due),
            "total_with_surcharge": str(installment.amount_due + (installment.amount_due * installment.surcharge_pct / 100)),
            'user_id': user.id,
            'installment_due_date': installment.due_date.isoformat(),
            'installment_state': installment.state,
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

        send_email_task.delay(  # type: ignore[attr-defined]
            email=user_email,
            template_id=template.id,
            context=context_data,
            log_email_id=notification_log.id if notification_log else None
        )

        logger.info(
            f"Notificación de cuota adeudada por mora encolada. "
            f"Usuario: {user.id}, Cuota: {installment.pk}, Email: {user_email}"
        )

    except Exception as e:
        error_message = f"Error enviando notificación de cuota adeudada por mora: {str(e)}"

        logger.error(
            f"Error enviando notificación de cuota adeudada por mora. "
            f"Usuario: {installment.purchase.user.id}, "
            f"Cuota: {installment.pk}, "
            f"Error: {error_message}"
        )
