from django.db import models
from api.purchases.models import Purchase
from decimal import Decimal
from django.conf import settings


class Installment(models.Model):
    """
    Modelo que representa las cuotas de una compra.

    Atributos:
        purchase (ForeignKey): Referencia a la compra asociada.
        num_installment (IntegerField): Número de la cuota.
        base_amount (DecimalField): Monto base a pagar por la cuota.
        surcharge_pct (DecimalFile): Recargo en porcentaje aplicado.
        discount_pct (DecimalFile): Descuento en porcentaje aplicado.
        amount_due (DecimalFile): Monto final a pagar de la cuota.
        due_date (DateField): Fecha límite para el pago de la cuota.
        state (CharField): Estado de la cuota: PENDING, PAID, o OVERDUE.
        paid_amount (DecimalFile): Monto pagado.
        paid_at (DateTime): Fecha y hora que se realizo el pago.
        updated_at(DateTimeField): Campo de auditoría almacena la fecha y hora que fue modificado el registro.
        created_at(DateTimeField): Campo de auditoría almacena la fecha y hora que fue creado el registro.
        updated_by(ForeignKey): Referencia al usuario que actualizo el registro.
    """
    class State(models.TextChoices):
        PENDING = "PENDING", "PENDING"
        PAID = "PAID", "PAID"
        OVERDUE = "OVERDUE", "OVERDUE"

    purchase = models.ForeignKey(
        Purchase, on_delete=models.CASCADE, related_name='installments')
    num_installment = models.PositiveIntegerField()
    base_amount = models.DecimalField(max_digits=12, decimal_places=2)
    surcharge_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0'))
    discount_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0'))
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    state = models.CharField(
        max_length=10, choices=State.choices, default=State.PENDING)
    paid_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)  # <-- no auto_now

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="installments_updated")

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=['purchase', 'num_installment'], name='uq_installment')]
        indexes = [
            models.Index(fields=['due_date'], name='idx_installment_due'),
            models.Index(fields=['state'], name='idx_installments_state'),
        ]


class Payment(models.Model):
    """
    Modelo para gestionar los pagos realizados por los usuarios en relación con sus compras.

    Atributos:
        installment (ForeignKey): Relación con el modelo Cuotas para identificar a qué compra pertenece el pago.
        payment_date (DateField): Fecha en la que se realizó el pago.
        amount (DecimalField): Monto total pagado por el usuario en este pago.
        payment_methods (CharField): Método utilizado para realizar el pago (CASH, CARD, TRANSFER). 
        external_ref (CharField): Referencia externa del pago, ej: 'numero de comprobante', 'código de transacción', etc.
        updated_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue modificado el registro.
        created_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue creado el registro.
        updated_by (ForeignKey): Referencia al usuario que actualizo el registro.
    """
    class Method(models.TextChoices):
        CASH = "CASH", "CASH"
        CARD = "CARD", "CARD"
        TRANSFER = "TRANSFER", "TRANSFER"

    installment = models.ForeignKey(Installment, on_delete=models.CASCADE)
    payment_date = models.DateTimeField(
        auto_now_add=True)  # <-- antes tenías auto_now
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(
        max_length=10, choices=Method.choices, default=Method.CASH)
    external_ref = models.CharField(
        max_length=120, null=True, blank=True, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="payments_updated")

    class Meta:
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['installment'],
                         name='idx_payment_installment'),
            models.Index(fields=['payment_date'], name='idx_payment_date'),
        ]
        constraints = [models.UniqueConstraint(
            fields=['external_ref'], name='uq_payment_extref')]
