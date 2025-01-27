from django.core.management.base import BaseCommand
from api.utils import enviar_correo


class Command(BaseCommand):
    help = 'Actualiza el estado de las cuotas vencidas y envía notificaciones'

    def handle(self, *args, **kwargs):
        try:
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
                                                <p>Estimado/a guille</p>
                                                    <p>Le informamos que su cuota con vencimiento el <strong>...</strong> se encuentra <b>pendiente de pago.</b></p>
                                                    
                                                    <p>Detalles de la cuota:</p>
                                                    <ul>
                                                        <li>Número de cuota: <strong>#...</strong></li>
                                                        <li>Monto adeudado: <strong>...</strong></li>
                                                        <li>Fecha de vencimiento: <strong>...</strong></li>
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
            # Enviar correo al usuario
            enviar_correo(
                email_destino="Tu_Email",
                asunto='Notificación: Su cuota está vencida',
                mensaje_html=mensaje_html
            )
            self.stdout.write(self.style.SUCCESS('Correo enviado con éxito.'))
        except Exception as e:
            self.stderr.write(f'Error al enviar el correo: {e}')
