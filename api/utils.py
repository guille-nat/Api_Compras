import os
import resend

resend.api_key = os.getenv("RESEND_API_KEY")


def enviar_correo(email_destino, asunto, mensaje):
    """
    Envía un correo usando la API de Resend.
    """
    params: resend.Emails.SendParams = {
        "from": f"Acme <onboarding@resend.dev>",
        "to": [f"{email_destino}"],
        "subject": f"{asunto}",
        "html": """<!DOCTYPE html>
                    <html lang="es">
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <title>Notificación de Cuota Vencida</title>
                        <style>
                            body {
                                font-family: Arial, sans-serif;
                                line-height: 1.6;
                                color: #333;
                                max-width: 600px;
                                margin: 0 auto;
                                padding: 20px;
                            }
                            .header {
                                background-color: #f44336;
                                color: white;
                                text-align: center;
                                padding: 20px;
                            }
                            .content {
                                background-color: #f9f9f9;
                                border: 1px solid #ddd;
                                padding: 20px;
                                margin-top: 20px;
                            }
                            .footer {
                                margin-top: 20px;
                                text-align: center;
                                font-size: 12px;
                                color: #777;
                            }
                            
                        </style>
                    </head>
                    <body>
                        <div class="header">
                            <h1>Notificación de Cuota Vencida</h1>
                        </div>
                        
                        <div class="content">
                            {mensaje}
                        </div>
                        
                        <div class="footer">
                            <p>Este es un mensaje automático, por favor no responda a este correo.</p>
                            <p>Recuerde que esta es una plantilla de prueba, no representa nada, solo a fin demostrativo.</p>
                            <p>&copy; 2024 Guillermo Natali Ulla. Todos los derechos reservados.</p>
                            <a href="https://nataliullacoder.com/" target="_blank">NataliUllaCoder</a>
                        </div>
                    </body>
                    </html>""",
    }
    email = resend.Emails.send(params)
    print(email)
