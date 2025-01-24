from django.db import models
from django.contrib.auth.models import User


class Products(models.Model):
    """
    Modelo que representa un producto en el inventario.

    Atributos:
        cod_products(CharField): Código único que identifica el producto.
        nombre (CharField): Nombre del producto.
        marca (CharField): Marca del producto.
        modelo (CharField): Modelo específico del producto.
        precio_unitario (DecimalField): Precio unitario del producto.
        stock (IntegerField): Cantidad de unidades disponibles en el inventario.
    """
    cod_products = models.CharField(
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
        Representación legible del objeto Products.
        """
        return f"{self.nombre} ({self.marca} - {self.modelo})"

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"


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

    def __str__(self):
        """
        Representación legible del objeto Compras.
        """
        return f"Compra {self.id} - Usuario: {self.usuario.username}"

    class Meta:
        verbose_name = "Compra"
        verbose_name_plural = "Compras"


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
        ('PENDIENTE', 'Pendiente'),
        ('PAGADA', 'Pagada'),
        ('ATRASADA', 'Atrasada'),
    ]
    compras = models.ForeignKey(
        Compras, on_delete=models.CASCADE, help_text="Compra asociada a la cuota.", related_name='cuotas')
    nro_cuota = models.PositiveIntegerField(help_text="Número de cuota.")
    monto = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Monto de la cuota a abonar.")
    fecha_vencimiento = models.DateField(
        help_text="Fecha en la cual vence la cuota.")
    estado = models.CharField(
        max_length=9, choices=ESTADOS, default='PENDIENTE', help_text="Estad de la cuota.")

    def __str__(self):
        """
        Representación legible del objeto Cuotas.
        """
        return f"Cuota {self.nro_cuota} - Compra {self.compra.id}"

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
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta'),
        ('TRANSFERENCIA', 'Transferencia'),
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


class DetallesCompras(models.Model):
    """
        compras (foreign key): Relación con el modelo Compras para poder determinar a que compra pertenece
        products (foreign key): Relación con el modelo Products para poder determinar que compra el usuario
        cantidad_producto (int): Cantidad del mismo producto compra el usuario
    """
    compras = models.ForeignKey(
        Compras, on_delete=models.CASCADE, help_text="Compra asociada al producto.", related_name='detalles')
    products = models.ForeignKey(
        Products, on_delete=models.CASCADE, help_text="Productos asociado a la compra.")
    cantidad_productos = models.PositiveIntegerField(
        help_text="Cantidad del producto.")

    def __str__(self):
        return f"Detalle de compra ID {self.id} - Compra ID {self.compras.id} - Producto: {self.products.id}"

    class Meta:
        verbose_name = "Detalle Compra"
        verbose_name_plural = "Detalles Compras"


class Notificacion(models.Model):
    """
    Modelo para gestionar notificaciones relacionadas con usuarios y compras.

    Atributos:
        usuario (ForeignKey): Usuario asociado a la notificación.
        compra (ForeignKey): Compra asociada a la notificación (opcional).
        cuota (ForeignKey): Cuota asociada a la notificación (opcional).
        mensaje (TextField): Mensaje de la notificación.
        fecha_creacion (DateTimeField): Fecha de creación de la notificación.
        enviada (BooleanField): Si la notificación ya fue enviada.
    """
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    compra = models.ForeignKey(
        Compras, on_delete=models.CASCADE, null=True, blank=True)
    cuota = models.ForeignKey(
        Cuotas, on_delete=models.CASCADE, null=True, blank=True)
    mensaje = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    enviada = models.BooleanField(default=False)

    def __str__(self):
        return f"Notificación para {self.usuario.username} - {self.mensaje[:30]}..."

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
