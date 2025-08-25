from django.db import models
from api.users.models import CustomUser
from api.products.models import Product


class Purchase(models.Model):
    """
    Modelo que representa una compra realizada por un usuario.

    Atributos:
        user (ForeignKey): Referencia al usuario que realizó la compra.
        purchase_date (DateField): Fecha en que se realizó la compra.
        due_date (DateField): Fecha límite para el pago.
        total_amount (DecimalField): Monto total de la compra.
        total_installments_count (int): Cantidad de cuotas en la que se divide la compra.
        current_installment (int): La cuota en la que se encuentra el usuario.
        discount_applied (DecimalField): Descuento aplicado al pago, si corresponde.
        amount_paid (DecimalField): Monto que ha sido pagado por el usuario hasta ahora.
    """
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, help_text="Usuario que realiza la compra.")
    purchase_date = models.DateField(
        help_text="Fecha en la cual la compra se realiza.")
    due_date = models.DateField(
        help_text="Fecha de vencimiento del pago.")
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Monto total de la compra.")
    total_installments_count = models.PositiveIntegerField(
        help_text="Total de cuotas a pagar.", default=1)
    discount_applied = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        default=0.0,
        help_text="Descuento aplicado en el pago, si corresponde."
    )
    current_installment = models.PositiveIntegerField(
        help_text="Cuota actual en la que se encuentra el pago.", default=1)
    amount_paid = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Monto que se ha pagado.", default=0.00)

    def __str__(self):
        """
        Representación legible del objeto Compra.
        """
        return f"Compra {self.id} - Usuario: {self.user.username}"

    class Meta:
        verbose_name = "Compra"
        verbose_name_plural = "Compras"


class PurchaseDetail(models.Model):
    """
    Modelo para representar el detalle de cada producto en una compra.
    Atributos:
        purchase (ForeignKey): Relación con el modelo Compra.
        product (ForeignKey): Relación con el modelo Producto.
        cant_product (int): Cantidad del mismo producto comprada.
    """
    purchase = models.ForeignKey(
        Purchase, on_delete=models.CASCADE, help_text="Compra asociada al producto.", related_name='details')
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, help_text="Producto asociado a la compra.")
    cant_product = models.PositiveIntegerField(
        help_text="Cantidad del producto comprado.")

    def __str__(self):
        return f"Detalle de compra ID {self.id} - Compra ID {self.purchase.id} - Producto: {self.product.id}"

    class Meta:
        verbose_name = "Detalle Compra"
        verbose_name_plural = "Detalles Compras"
