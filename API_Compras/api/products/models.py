from django.db import models
from api.categories.models import Category
from django.conf import settings
from decimal import Decimal


class ProductCategory(models.Model):
    """
    Modelo intermedio que representa la relación entre productos y categorías.

    Permite establecer múltiples categorías por producto y agregar metadatos
    adicionales a la relación como fecha de asignación y usuario responsable.

    Atributos:
        product (ForeignKey): Referencia al producto.
        category (ForeignKey): Referencia a la categoría.
        is_primary (BooleanField): Indica si es la categoría principal del producto.
        assigned_at (DateTimeField): Fecha y hora de asignación de la categoría.
        assigned_by (ForeignKey): Usuario que asignó la categoría al producto.
    """
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        help_text='Producto asociado'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        help_text='Categoría asociada'
    )
    is_primary = models.BooleanField(
        default=False,
        help_text='Indica si es la categoría principal del producto'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Usuario que asignó la categoría'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'category'],
                name='uq_product_category'
            )
        ]
        indexes = [
            models.Index(fields=['product'], name='idx_pc_product'),
            models.Index(fields=['category'], name='idx_pc_category'),
            models.Index(fields=['is_primary'], name='idx_pc_primary'),
        ]
        verbose_name = 'Categoría de Producto'
        verbose_name_plural = 'Categorías de Productos'


class Product(models.Model):
    """
    Modelo que representa un producto en el inventario.

    Atributos:
        product_code(CharField): Código único que identifica el producto.
        name (CharField): Nombre del producto.
        brand (CharField): Marca del producto.
        model (CharField): Modelo específico del producto.
        unit_price (DecimalField): Precio unitario del producto.
        categories (ManyToManyField): Referencia a las categorías asociadas mediante tabla intermedia.
        description (TextField): Descripción detallada del producto.
        created_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue creado el registro.
        updated_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue modificado el registro.
        created_by (ForeignKey): Referencia al usuario que creó el registro.
        updated_by (ForeignKey): Referencia al usuario que actualizo el registro.
    """
    product_code = models.CharField(max_length=120, unique=True)
    name = models.CharField(max_length=120)
    brand = models.CharField(max_length=120, blank=True, default="")
    model = models.CharField(max_length=120, blank=True, default="")
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.0'))

    # Relación muchos a muchos con tabla intermedia personalizada
    categories = models.ManyToManyField(
        Category,
        through='ProductCategory',
        related_name='products',
        help_text='Categorías asociadas a este producto'
    )
    description = models.TextField(blank=True, default="")

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
        indexes = [
            models.Index(fields=['name'], name='idx_product_name'),
        ]

    def get_primary_category(self):
        """
        Obtiene la categoría principal del producto.

        Returns:
            Category: La categoría marcada como principal, None si no existe.
        """
        try:
            return self.categories.get(productcategory__is_primary=True)
        except Category.DoesNotExist:
            return None

    def set_primary_category(self, category, user=None):
        """
        Establece una categoría como principal para el producto.

        Args:
            category (Category): La categoría a establecer como principal.
            user (User, optional): Usuario que realiza la operación.

        Raises:
            ValueError: Si la categoría no está asociada al producto.
        """
        # Quitar marca de principal a todas las categorías actuales
        ProductCategory.objects.filter(
            product=self, is_primary=True).update(is_primary=False)

        # Establecer la nueva categoría principal
        try:
            pc = ProductCategory.objects.get(product=self, category=category)
            pc.is_primary = True
            if user:
                pc.assigned_by = user
            pc.save()
        except ProductCategory.DoesNotExist:
            raise ValueError(
                f"La categoría {category.name} no está asociada a este producto")
