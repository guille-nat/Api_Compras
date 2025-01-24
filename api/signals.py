from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Cuotas, Notificacion
from datetime import date
from .utils import enviar_correo


@receiver(post_save, sender=Cuotas)
def crear_notificacion_cuota(sender, instance, created, **kwargs):
    """
    Crea una notificación cuando una cuota cambia de estado.
    """
    if not created:  # Si la cuota ya existía y se actualizó
        if instance.fecha_vencimiento < date.today() and not instance.pagada:
            mensaje = f"""
            <p>Estimado/a cliente,</p>
            <p>Le informamos que su cuota con vencimiento el <strong>{instance.fecha_vencimiento}</strong> se encuentra pendiente de pago.</p>
            
            <p>Detalles de la cuota:</p>
            <ul>
                <li>Número de cuota: <strong>#{instance.nro_cuota}</strong></li>
                <li>Monto adeudado: <strong>{instance.monto}</strong></li>
                <li>Fecha de vencimiento: <strong>{instance.fecha_vencimiento}</strong></li>
            </ul>
            
            <p>Le recordamos la importancia de mantener sus pagos al día para evitar recargos adicionales y posibles interrupciones en el servicio.</p>
            
            <p>Si ya ha realizado el pago, por favor ignore este mensaje. En caso contrario, le invitamos a regularizar su situación lo antes posible.</p>
            """
            Notificacion.objects.create(
                usuario=instance.compra.usuario,
                compra=instance.compra,
                cuota=instance,
                mensaje=mensaje
            )
            enviar_correo(
                email_destino=instance.compra.usuario.email,
                asunto='Notificación su cuota esta Vencida',
                mensaje=f'{mensaje}'
            )
