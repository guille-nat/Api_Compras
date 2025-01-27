from django.db import models
from django.contrib.auth.models import User
from api.compras.models import Compras
from api.pagos.models import Cuotas


class Notificacion(models.Model):
    """
    Modelo para gestionar notificaciones relacionadas con usuarios y compras.

    Atributos:
        usuario (ForeignKey): Usuario asociado a la notificación.
        compra (ForeignKey): Compra asociada a la notificación (opcional).
        cuota (ForeignKey): Cuota asociada a la notificación (opcional).
        mensaje (TextField): Mensaje de la notificación.
        fecha_creacion (DateTimeField): Fecha de creación de la notificación.
        enviada (BooleanField): Si la notificación ya fue enviada.
    """
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    compra = models.ForeignKey(
        Compras, on_delete=models.CASCADE, null=True, blank=True)
    cuota = models.ForeignKey(
        Cuotas, on_delete=models.CASCADE, null=True, blank=True)
    mensaje = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    enviada = models.BooleanField(default=False)

    def __str__(self):
        return f"Notificación para {self.usuario.username} - {self.mensaje[:30]}..."

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
