from django.db import models
from api.compras.models import Compras


class Cuotas(models.Model):
    """
    Modelo que representa las cuotas de una compra.

    Atributos:
        compra (ForeignKey): Referencia a la compra asociada.
        nro_cuota (IntegerField): Número de la cuota.
        monto (DecimalField): Monto a pagar por la cuota.
        fecha_vencimiento (DateField): Fecha límite para el pago de la cuota.
        estado (CharField): Estado de la cuota: PENDIENTE, PAGADA, o ATRASADA.
    """
    ESTADOS = [
        ('PENDIENTE', 'PENDIENTE'),
        ('PAGADA', 'PAGADA'),
        ('ATRASADA', 'ATRASADA'),
    ]
    compras = models.ForeignKey(
        Compras, on_delete=models.CASCADE, help_text="Compra asociada a la cuota.", related_name='cuotas'
    )
    nro_cuota = models.PositiveIntegerField(help_text="Número de cuota.")
    monto = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Monto de la cuota a abonar."
    )
    fecha_vencimiento = models.DateField(
        help_text="Fecha en la cual vence la cuota.")
    estado = models.CharField(
        max_length=9, choices=ESTADOS, default='PENDIENTE', help_text="Estado de la cuota."
    )

    def __str__(self):
        """
        Representación legible del objeto Cuotas.
        """
        return f"Cuota {self.nro_cuota} - Compra {self.compras.id}"

    class Meta:
        verbose_name = "Cuota"
        verbose_name_plural = "Cuotas"


class Pagos(models.Model):
    """
    Modelo para gestionar los pagos realizados por los usuarios en relación con sus compras.

    Atributos:
        cuotas (ForeignKey): Relación con el modelo Cuotas para identificar a qué compra pertenece el pago.
        fecha_pago (DateField): Fecha en la que se realizó el pago.
        monto (DecimalField): Monto total pagado por el usuario en este pago.
        medio_pago (CharField): Método utilizado para realizar el pago (Efectivo, Tarjeta, Transferencia).
    """
    MEDIOS_PAGO = [
        ('EFECTIVO', 'EFECTIVO'),
        ('TARJETA', 'TARJETA'),
        ('TRANSFERENCIA', 'TRANSFERENCIA'),
    ]

    cuotas = models.ForeignKey(
        Cuotas, on_delete=models.CASCADE, null=False, help_text="Cuota asociada al pago.")
    fecha_pago = models.DateField(
        null=False, help_text="Fecha en la que se realizó el pago.")
    monto = models.DecimalField(
        max_digits=10, decimal_places=2, null=False, help_text="Monto total del pago.")
    medio_pago = models.CharField(
        max_length=20,
        choices=MEDIOS_PAGO,
        default='EFECTIVO',
        help_text="Medio utilizado para realizar el pago."
    )

    def __str__(self):
        return f"Pago ID {self.id} - Compra ID {self.cuotas.id} - Monto: {self.monto}"

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ['-fecha_pago']
