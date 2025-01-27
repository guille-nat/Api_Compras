from django.core.management.base import BaseCommand
from datetime import date, timedelta
from api.models import Cuotas, Notificacion
from api.utils import enviar_correo
from decimal import Decimal
import logging


class Command(BaseCommand):
    help = 'Actualiza el estado de las cuotas vencidas y envía notificaciones'

    def handle(self, *args, **kwargs):
        try:
            logger = logging.getLogger(__name__)
            # Obtener todas las cuotas pendientes con fecha de vencimiento menor o igual a hoy
            cuotas_vencidas = Cuotas.objects.filter(
                fecha_vencimiento__lte=date.today(),
                estado='PENDIENTE'  # Solo cuotas pendientes
            )

            logger.info(
                f"Cuotas vencidas encontradas: {cuotas_vencidas.count()}")

            for cuota in cuotas_vencidas:
                # Actualizar el estado de la cuota a ATRASADA
                cuota.estado = 'ATRASADA'
                recargo = Decimal('0.08')  # Recargo del 8%
                total_recargado = cuota.monto * recargo
                cuota.monto += round(total_recargado, 2)
                cuota.fecha_vencimiento += timedelta(days=15)
                cuota.save()
                detalles = cuota.compras.detalles.all()
                productos = '\n'.join(
                    [str(detalle.products)
                     for detalle in detalles]
                )
                # Obtener el usuario asociado
                usuario = cuota.compras.usuario

                # Crear el mensaje de notificación
                mensaje_html = f"""<!DOCTYPE html>
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
                                        <p>Estimado/a {usuario.username}</p>
                                            <p>Le informamos que su cuota con vencimiento el <strong>{cuota.fecha_vencimiento}</strong> se encuentra <b>pendiente de pago.</b></p>
                                            
                                            <p>Detalles de la cuota:</p>
                                            <ul>
                                                <li><strong>Productos: </strong><pre>{productos}</pre></li>
                                                <li>Número de cuota: <strong>#{cuota.nro_cuota}</strong></li>
                                                <li>Monto adeudado: <strong>${round(cuota.monto,2):,.2f}</strong></li>
                                                <li>Fecha de vencimiento: <strong>{cuota.fecha_vencimiento}</strong></li>
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
                mensaje = f"""Estimado/a {usuario.username}, Le informamos que su cuota con vencimiento el {cuota.fecha_vencimiento} se encuentra pendiente de pago.
                Número de cuota: #{cuota.nro_cuota},Monto adeudado: ${cuota.monto:,.2f}, Fecha de vencimiento: <strong>{cuota.fecha_vencimiento},
                Le recordamos la importancia de mantener sus pagos al día para evitar recargos adicionales."""
                # Crear notificación en el sistema
                Notificacion.objects.create(
                    usuario=usuario,
                    compra=cuota.compras,
                    cuota=cuota,
                    mensaje=mensaje
                )

                # Enviar correo al usuario
                enviar_correo(
                    email_destino=str(usuario.email),
                    asunto='Notificación: Su cuota está vencida',
                    mensaje_html=mensaje_html
                )

            # Imprimir el resultado de la operación
            self.stdout.write(
                self.style.SUCCESS(
                    f"Se actualizaron {cuotas_vencidas.count()} cuotas vencidas."
                )
            )
        except Exception as e:
            self.stderr.write(f"Error: {e}")
