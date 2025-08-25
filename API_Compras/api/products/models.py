from django.db import models
from api.categories.models import Category
from django.conf import settings
from decimal import Decimal


class Product(models.Model):
    """
    Modelo que representa un producto en el inventario.

    Atributos:
        product_code(CharField): Código único que identifica el producto.
        name (CharField): Nombre del producto.
        brand (CharField): Marca del producto.
        model (CharField): Modelo específico del producto.
        unit_price (DecimalField): Precio unitario del producto.
        category (ForeignKey): Referencia a la categoría asociada.
        updated_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue modificado el registro.
        created_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue creado el registro.
        created_by (ForeignKey): Referencia al usuario que creó el registro.
        updated_by (ForeignKey): Referencia al usuario que actualizo el registro.
    """
    product_code = models.CharField(max_length=120, unique=True)
    name = models.CharField(max_length=180)
    brand = models.CharField(max_length=120, blank=True, default="")
    model = models.CharField(max_length=120, blank=True, default="")
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0'))
    category = models.ForeignKey(Category, on_delete=models.PROTECT)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="products_created")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="products_updated")

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=['product_code'], name='uq_product_code')]
        indexes = [models.Index(fields=['category'],
                                name='idx_product_category')]
