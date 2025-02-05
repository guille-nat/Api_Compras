from django.core.mail import send_mail
from django.http import HttpResponse
import os
from dotenv import load_dotenv


def sendEmail(destination_email, subject, message_html):
    """
    Envía un correo usando la API de Resend.
    """
    try:
        load_dotenv()
        send_mail(
            subject=subject,
            message='',
            from_email=os.getenv('EMAIL_HOST_USER'),
            recipient_list=[destination_email],
            fail_silently=False,
            html_message=message_html
        )
        return HttpResponse('Correo enviado con éxito')
    except Exception as e:
        print(f"Error enviando el correo: {e}")
