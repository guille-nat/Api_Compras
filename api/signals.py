from django.db.models.signals import post_save
from django.dispatch import receiver
from api.payments.models import Installment
from .models import Notification
from datetime import date
from .utils import sendEmail


@receiver(post_save, sender=Installment)
def create_notification_installment(sender, instance, created, **kwargs):
    """
    Crea una notificación cuando una cuota cambia de estado Pagado y envía la notificación.
    """

    if not created:  # Si la cuota ya existía y se actualizó
        if instance.state == 'PAGADA':
            details = instance.purchase.details.all()
            product = '\n'.join(
                [str(detail.product)
                 for detail in details]
            )
            message_html = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Confirmación de Pago Exitoso</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                        padding-top: 5px;
                    }}
                    .header {{
                        background-color: #4CAF50;
                        color: white;
                        text-align: center;
                        padding: 20px;
                    }}
                    .content {{
                        background-color: #f9f9f9;
                        border: 1px solid #ddd;
                        padding: 20px;
                        margin-top: 20px;
                    }}
                    .footer {{
                        margin-top: 10px;
                        text-align: center;
                        font-size: 12px;
                        color: #777;
                    }}
                    .footer a{{
                        color: #fff;
                    }}
                    a {{
                        display: inline-block;
                        background-color: #4CAF50;
                        color: #fff;
                        padding: 10px 20px;
                        text-decoration: none;
                        border-radius: 5px;
                        }}
                    .payment-details {{
                        background-color: #e7f3fe;
                        border-left: 6px solid #2196F3;
                        margin-bottom: 15px;
                        padding: 10px;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>¡Pago Realizado con Éxito!</h1>
                </div>

                <div class="content">
                    <p>Estimado/a {instance.purchase.user.username}</p>
                    <p>Con nombre: {instance.purchase.user.first_name}, {instance.purchase.user.last_name}</p>
                    

                    <p>Nos complace confirmarle que hemos recibido su pago correctamente. Agradecemos su puntualidad y confianza en
                        nuestros servicios.</p>

                    <div class="payment-details">
                        <p><strong>Detalles del pago:</strong></p>
                        <ul>
                            <li><strong>Productos: </strong><pre>{product}</pre></li>
                            <li>Número de cuota: <strong>{instance.num_installment}</strong></li>
                            <li>Monto pagado: <strong>${instance.amount:,.2f}</strong></li>
                            <li>Fecha de pago: <strong>{date.today()}</strong></li>
                            <li>Con fecha de vencimiento: <strong>{instance.due_date_installment}</strong></li>
                        </ul>
                    </div>

                    <p>Este pago ha sido aplicado a su cuenta y su saldo ha sido actualizado.</p>

                </div>

                <div class="footer">
                    <p>Gracias por su preferencia. Valoramos su confianza en nosotros.</p>
                    <p>Este es un mensaje automático, por favor no responda a este correo.</p>
                    <p>Recuerde que esta es una plantilla de prueba, no representa nada, solo a fin demostrativo.</p>
                    <p>&copy; 2024 Guillermo Natali Ulla. Todos los derechos reservados.</p>
                    <a href="https://nataliullacoder.com/" target="_blank">NataliUllaCoder</a>
                </div>
            </body>
            </html>"""
            message = f"""Estimado/a {instance.purchase.user.username},Número de cuota: {instance.num_installment},
            Monto pagado: ${instance.amount:,.2f}, Fecha de pago: {date.today()},Con fecha de vencimiento: {instance.due_date_installment},
            Este pago ha sido aplicado a su cuenta y su saldo ha sido actualizado."""

            Notification.objects.create(
                user=instance.purchase.user,
                purchase=instance.purchase,
                installment=instance,
                message=message
            )
            sendEmail(
                destination_email=str(instance.purchase.user.email),
                subject='Notificación su cuota esta Pagada',
                message_html=message_html
            )
