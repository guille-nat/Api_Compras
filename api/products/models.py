from django.db import models


class Product(models.Model):
    """
    Modelo que representa un producto en el inventario.

    Atributos:
        product_code(CharField): Código único que identifica el producto.
        name (CharField): Nombre del producto.
        brand (CharField): Marca del producto.
        model (CharField): Modelo específico del producto.
        unit_price (DecimalField): Precio unitario del producto.
        stock (IntegerField): Cantidad de unidades disponibles en el inventario.
    """
    product_code = models.CharField(
        max_length=40, unique=True, help_text="Código del producto.")
    name = models.CharField(max_length=100, help_text="Nombre del producto.")
    brand = models.CharField(
        max_length=45,  help_text="Marca asociada al producto.")
    model = models.CharField(
        max_length=100,  help_text="Modelo asociado al producto.")
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2,  help_text="Precio del producto por unidad.")
    stock = models.PositiveIntegerField(
        help_text="Cantidad del producto en stock")

    def save(self, *args, **kwargs):
        # Convertir campos necesarios a minúsculas antes de guardar
        self.name = self.name.lower()
        self.brand = self.brand.lower()
        self.model = self.model.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        """
        Representación legible del objeto Productos.
        """
        return f"{self.name} ({self.brand} - {self.model})"

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
