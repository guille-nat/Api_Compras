from django.core.management.base import BaseCommand
from datetime import date, timedelta
from api.payments.models import Installment
from api.models import Notification
from api.utils import sendEmail
from decimal import Decimal
import logging


class Command(BaseCommand):
    help = 'Actualiza el estado de las cuotas vencidas y envía notificaciones'

    def handle(self, *args, **kwargs):
        try:
            logger = logging.getLogger(__name__)
            # Obtener todas las cuotas pendientes con fecha de vencimiento menor o igual a hoy
            due_installment = Installment.objects.filter(
                due_date_installment__lte=date.today(),
                state='PENDIENTE'  # Solo cuotas pendientes
            )

            logger.info(
                f"Cuotas vencidas encontradas: {due_installment.count()}")

            for installment in due_installment:
                # Actualizar el estado de la cuota a ATRASADA
                installment.state = 'ATRASADA'
                recargo = Decimal('0.08')  # Recargo del 8%
                total_recargado = installment.amount * recargo
                installment.amount += round(total_recargado, 2)
                installment.due_date_installment += timedelta(days=15)
                installment.save()
                details = installment.purchase.details.all()
                product = '\n'.join(
                    [str(detail.product)
                     for detail in details]
                )
                # Obtener el usuario asociado
                user = installment.purchase.user

                # Crear el mensaje de notificación
                message_html = f"""<!DOCTYPE html>
                                <html lang="es">
                                <head>
                                    <meta charset="UTF-8">
                                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                    <title>Notificación de Cuota Vencida</title>
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
                                            background-color: #f44336;
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
                                        .footer{{
                                            margin-top: 10px;
                                            text-align: center;
                                            font-size: 12px;
                                            color: #777;
                                        }}
                                        .footer a{{
                                            color:#fff;
                                        }}
                                        a{{
                                            display: inline-block;
                                            background-color: #4CAF50;
                                            color: white;
                                            padding: 10px 20px;
                                            text-decoration: none;
                                            border-radius: 5px;
                                            text-decoration: none;
                                        }}
                                        
                                    </style>
                                </head>
                                <body>
                                    <div class="header">
                                        <h1>Notificación de Cuota Vencida</h1>
                                    </div>
                                    
                                    <div class="content">
                                        <p>Estimado/a {user.username}</p>
                                            <p>Con nombre: {user.first_name}, {user.last_name}</p>
                                            <p>Le informamos que su cuota con vencimiento el <strong>{installment.due_date_installment}</strong> se encuentra <b>pendiente de pago.</b></p>
                                            
                                            <p>Detalles de la cuota:</p>
                                            <ul>
                                                <li><strong>Productos: </strong><pre>{product}</pre></li>
                                                <li>Número de cuota: <strong>#{installment.num_installment}</strong></li>
                                                <li>Monto adeudado: <strong>${round(installment.amount,2):,.2f}</strong></li>
                                                <li>Fecha de vencimiento: <strong>{installment.due_date_installment}</strong></li>
                                            </ul>
                                            
                                            <p>Le recordamos la importancia de mantener sus pagos al día para evitar recargos adicionales.</p> 
                                    </div>
                                    
                                    <div class="footer">
                                        <p>Este es un mensaje automático, por favor no responda a este correo.</p>
                                        <p>Recuerde que esta es una plantilla de prueba, no representa nada, solo a fin demostrativo.</p>
                                        <p>&copy; 2024 Guillermo Natali Ulla. Todos los derechos reservados.</p>
                                        <a href="https://nataliullacoder.com/" target="_blank">NataliUllaCoder</a>
                                    </div>
                                </body>
                                </html>  
                """
                message = f"""Estimado/a {user.username}, Le informamos que su cuota con vencimiento el {installment.due_date_installment} se encuentra pendiente de pago.
                Número de cuota: #{installment.num_installment},Monto adeudado: ${installment.amount:,.2f}, Fecha de vencimiento: <strong>{installment.due_date_installment},
                Le recordamos la importancia de mantener sus pagos al día para evitar recargos adicionales."""
                # Crear notificación en el sistema
                Notification.objects.create(
                    user=user,
                    purchase=installment.purchase,
                    installment=installment,
                    message=message
                )

                # Enviar correo al usuario
                sendEmail(
                    destination_email=str(user.email),
                    subject='Notificación: Su cuota está vencida',
                    message_html=message_html
                )

            # Imprimir el resultado de la operación
            self.stdout.write(
                self.style.SUCCESS(
                    f"Se actualizaron {due_installment.count()} cuotas vencidas."
                )
            )
        except Exception as e:
            self.stderr.write(f"Error: {e}")
