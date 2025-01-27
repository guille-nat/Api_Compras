from django.db import models


class Productos(models.Model):
    """
    Modelo que representa un producto en el inventario.

    Atributos:
        cod_productos(CharField): Código único que identifica el producto.
        nombre (CharField): Nombre del producto.
        marca (CharField): Marca del producto.
        modelo (CharField): Modelo específico del producto.
        precio_unitario (DecimalField): Precio unitario del producto.
        stock (IntegerField): Cantidad de unidades disponibles en el inventario.
    """
    cod_productos = models.CharField(
        max_length=40, unique=True, help_text="Código del producto.")
    nombre = models.CharField(max_length=100, help_text="Nombre del producto.")
    marca = models.CharField(
        max_length=45,  help_text="Marca asociada al producto.")
    modelo = models.CharField(
        max_length=100,  help_text="Modelo asociado al producto.")
    precio_unitario = models.DecimalField(
        max_digits=10, decimal_places=2,  help_text="Precio del producto por unidad.")
    stock = models.PositiveIntegerField(
        help_text="Cantidad del producto en stock")

    def __str__(self):
        """
        Representación legible del objeto Productos.
        """
        return f"{self.nombre} ({self.marca} - {self.modelo})"

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
