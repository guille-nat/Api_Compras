from django.core.mail import send_mail
from django.http import HttpResponse
import os
from dotenv import load_dotenv


def enviar_correo(email_destino, asunto, mensaje_html):
    """
    Envía un correo usando la API de Resend.
    """
    try:
        load_dotenv()
        send_mail(
            subject=asunto,
            message='',
            from_email=os.getenv('EMAIL_HOST_USER'),
            recipient_list=[email_destino],
            fail_silently=False,
            html_message=mensaje_html
        )
        return HttpResponse('Correo enviado con éxito')
    except Exception as e:
        print(f"Error enviando el correo: {e}")
