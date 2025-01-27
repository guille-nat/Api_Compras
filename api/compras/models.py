from django.db import models
from django.contrib.auth.models import User
from api.productos.models import Productos


class Compras(models.Model):
    """
    Modelo que representa una compra realizada por un usuario.

    Atributos:
        usuario (ForeignKey): Referencia al usuario que realizó la compra.
        fecha_compra (DateField): Fecha en que se realizó la compra.
        fecha_vencimiento (DateField): Fecha límite para el pago.
        monto_total (DecimalField): Monto total de la compra.
        cuotas_totales (int): Cantidad de cuotas en la que se divide la compra.
        cuota_actual (int): La cuota en la que se encuentra en la actualidad.
        descuento_aplicado (DecimalField): Descuento aplicado al pago, si corresponde.
        monto_pagado (DecimalField): indica el monto que pago el usuario hasta ahora.
    """
    usuario = models.ForeignKey(
        User, on_delete=models.CASCADE, help_text="Usuario que realiza la compra.")
    fecha_compra = models.DateField(
        help_text="Fecha en la cual la compra se realiza.")
    fecha_vencimiento = models.DateField(
        help_text="Fecha de vencimiento del pago.")
    monto_total = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Monto total de la compra.")
    cuotas_totales = models.PositiveIntegerField(
        help_text="Total de cuotas a pagar.", default=1)
    descuento_aplicado = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Descuento aplicado en el pago, si corresponde."
    )
    cuota_actual = models.PositiveIntegerField(
        help_text="Total de cuotas a pagar.", default=1)
    monto_pagado = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Monto que se ha pagado.", default=0.00)

    def __str__(self):
        """
        Representación legible del objeto Compras.
        """
        return f"Compra {self.id} - Usuario: {self.usuario.username}"

    class Meta:
        verbose_name = "Compra"
        verbose_name_plural = "Compras"


class DetallesCompras(models.Model):
    """
        compras (foreign key): Relación con el modelo Compras para poder determinar a que compra pertenece
        productos (foreign key): Relación con el modelo Productos para poder determinar que compra el usuario
        cantidad_producto (int): Cantidad del mismo producto compra el usuario
    """
    compras = models.ForeignKey(
        Compras, on_delete=models.CASCADE, help_text="Compra asociada al producto.", related_name='detalles')
    productos = models.ForeignKey(
        Productos, on_delete=models.CASCADE, help_text="Productos asociado a la compra.")
    cantidad_productos = models.PositiveIntegerField(
        help_text="Cantidad del producto.")

    def __str__(self):
        return f"Detalle de compra ID {self.id} - Compra ID {self.compras.id} - Producto: {self.productos.id}"

    class Meta:
        verbose_name = "Detalle Compra"
        verbose_name_plural = "Detalles Compras"
