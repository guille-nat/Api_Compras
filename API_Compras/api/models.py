from django.db import models
from api.users.models import CustomUser
from api.purchases.models import Purchase
from api.payments.models import Installment


class Notification(models.Model):
    """
    Modelo para gestionar notificaciones relacionadas con usuarios y compras.

    Atributos:
        user (ForeignKey): Usuario asociado a la notificación.
        purchase (ForeignKey): Compra asociada a la notificación (opcional).
        installment (ForeignKey): Cuota asociada a la notificación (opcional).
        message (TextField): Mensaje de la notificación.
        created_at (DateTimeField): Fecha de creación de la notificación.
        sended (BooleanField): Si la notificación ya fue enviada.
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    purchase = models.ForeignKey(
        Purchase, on_delete=models.CASCADE, null=True, blank=True)  # Purchase
    installment = models.ForeignKey(
        Installment, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    sended = models.BooleanField(default=False)

    def __str__(self):
        return f"Notificación para {self.user.username} - {self.message[:30]}..."

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
