from django.db import models
from api.products.models import Product
from django.conf import settings
from decimal import Decimal


class Purchase(models.Model):
    """
    Modelo que representa una compra realizada por un usuario.

    Atributos:
        user (ForeignKey): Referencia al usuario que realizó la compra.
        purchase_date (DateTimeField): Fecha en que se realizó la compra.
        total_amount (DecimalField): Monto total de la compra.
        total_installments_count (int): Cantidad de cuotas en la que se divide la compra.
        status (CharFile): Estado de la compra [OPEN, PAID, CANCELLED].
        discount_applied (DecimalField): Descuento aplicado al pago, si corresponde.
        updated_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue modificado el registro.
        created_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue creado el registro.
        created_by (ForeignKey): Referencia al usuario que creo el registro. 
        updated_by (ForeignKey): Referencia al usuario que actualizo el registro.
    """
    class Status(models.TextChoices):
        OPEN = "OPEN", "OPEN"
        PAID = "PAID", "PAID"
        CANCELLED = "CANCELLED", "CANCELLED"

    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    purchase_date = models.DateTimeField()
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0'))
    total_installments_count = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.OPEN)
    discount_applied = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="purchase_created")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="purchase_updated")

    class Meta:
        indexes = [
            models.Index(fields=['user'], name='idx_purchase_user'),
            models.Index(fields=['status'], name='idx_purchase_status'),
            models.Index(fields=['purchase_date'], name='idx_purchase_date'),
        ]
        verbose_name = "Compra"
        verbose_name_plural = "Compras"


class PurchaseDetail(models.Model):
    """
    Modelo para representar el detalle de cada producto en una compra.
    Atributos:
        purchase (ForeignKey): Relación con el modelo Compra.
        product (ForeignKey): Relación con el modelo Producto.
        quantity (int): Cantidad del mismo producto comprada.
        unit_price_at_purchase (DecimalField): Precio unitario del Producto.
        subtotal (DecimalField): Subtotal del producto por la cantidad seleccionada.
        updated_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue modificado el registro.
        created_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue creado el registro.
        updated_by (ForeignKey): Referencia al usuario que actualizo el registro.
    """
    purchase = models.ForeignKey(
        Purchase, on_delete=models.CASCADE, help_text="Compra asociada al producto.", related_name='details', null=False)
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, help_text="Producto asociado a la compra.", null=False)
    quantity = models.PositiveIntegerField(
        help_text="Cantidad del producto comprado.", null=False)
    unit_price_at_purchase = models.DecimalField(
        max_digits=10, decimal_places=2, help_text='Precio unitario del producto.', null=False)
    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2, help_text='Subtotal de producto.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="purchase_detail_updated"
    )

    class Meta:
        verbose_name = "Detalle Compra"
        verbose_name_plural = "Detalles Compras"
        indexes = [
            models.Index(fields=['purchase'], name='idx_pd_purchase'),
            models.Index(fields=['product'], name='idx_pd_product')
        ]
