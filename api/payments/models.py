from django.db import models
from api.purchases.models import Purchase


class Installment(models.Model):
    """
    Modelo que representa las cuotas de una compra.

    Atributos:
        purchase (ForeignKey): Referencia a la compra asociada.
        num_installment (IntegerField): Número de la cuota.
        amount (DecimalField): Monto a pagar por la cuota.
        due_date_installment (DateField): Fecha límite para el pago de la cuota.
        state (CharField): Estado de la cuota: PENDIENTE, PAGADA, o ATRASADA.
    """
    STATES = [
        ('PENDIENTE', 'PENDIENTE'),
        ('PAGADA', 'PAGADA'),
        ('ATRASADA', 'ATRASADA'),
    ]
    purchase = models.ForeignKey(
        Purchase, on_delete=models.CASCADE, help_text="Compra asociada a la cuota.", related_name='cuotas'
    )
    num_installment = models.PositiveIntegerField(help_text="Número de cuota.")
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Monto de la cuota a abonar."
    )
    due_date_installment = models.DateField(
        help_text="Fecha en la cual vence la cuota.")
    state = models.CharField(
        max_length=9, choices=STATES, default='PENDIENTE', help_text="Estado de la cuota."
    )

    def __str__(self):
        """
        Representación legible del objeto Cuotas.
        """
        return f"Cuota {self.num_installment} - Compra {self.purchase.id}"

    class Meta:
        verbose_name = "Cuota"
        verbose_name_plural = "Cuotas"


class Payment(models.Model):
    """
    Modelo para gestionar los pagos realizados por los usuarios en relación con sus compras.

    Atributos:
        installment (ForeignKey): Relación con el modelo Cuotas para identificar a qué compra pertenece el pago.
        payment_date (DateField): Fecha en la que se realizó el pago.
        amount (DecimalField): Monto total pagado por el usuario en este pago.
        payment_methods (CharField): Método utilizado para realizar el pago (Efectivo, Tarjeta, Transferencia).
    """
    PAYMENT_METHODS = [
        ('EFECTIVO', 'EFECTIVO'),
        ('TARJETA', 'TARJETA'),
        ('TRANSFERENCIA', 'TRANSFERENCIA'),
    ]

    installment = models.ForeignKey(
        Installment, on_delete=models.CASCADE, null=False, help_text="Cuota asociada al pago.")
    payment_date = models.DateField(
        null=False, help_text="Fecha en la que se realizó el pago.")
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=False, help_text="Monto total del pago.")
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default='EFECTIVO',
        help_text="Medio utilizado para realizar el pago."
    )

    def __str__(self):
        return f"Pago ID {self.id} - Compra ID {self.installment.id} - Monto: {self.amount}"

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ['-payment_date']
