from django.db import models
from api.products.models import Product
from api.storage_location.models import StorageLocation
from django.conf import settings
from datetime import date


class InventoryRecord(models.Model):
    """
    Modelo para gestionar el inventario de un producto

    Atributos:
        product (ForeignKey): Identificador del producto.
        location (ForeignKey): Identificador del depósito.
        quantity (PositiveIntegerField): Cantidad de productos.
        batch_code (CharField): Código de lote.
        expiry_date (Datefield): Fecha de expiración del lote.
        updated_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue modificado el registro.
        created_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue creado el registro.
        updated_by (ForeignKey): Referencia al usuario que actualizo el registro.
    """
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, null=False, help_text='Identificador del Producto.')
    location = models.ForeignKey(StorageLocation, on_delete=models.PROTECT,
                                 null=False, help_text='Identificador del Depósito.')
    quantity = models.PositiveIntegerField(
        null=False, help_text='Cantidad de productos.')
    batch_code = models.CharField(
        max_length=120, null=False, blank=True,
        default="__NULL__", help_text="Código de lote (si corresponde)"
    )
    expiry_date = models.DateField(
        null=False, blank=True,
        default=date(9999, 12, 31), help_text="Fecha de vencimiento del lote"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="inventory_record_updated"
    )

    class Meta:
        verbose_name = "Inventario"
        verbose_name_plural = "Inventarios"
        ordering = ['product', '-quantity']
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'location', 'batch_code', 'expiry_date'],
                name='uq_invrec'
            )
        ]
        indexes = [
            models.Index(fields=['product'], name='idx_invrc_product'),
            models.Index(fields=['location'], name='idx_invrec_location'),
            models.Index(fields=["product", "location",
                         "batch_code", "expiry_date"], name="idx_invrec_prod_loc_bat_exp"),
        ]


class InventoryMovement(models.Model):
    """
    Modelo para gestionar los movimientos de productos 

    Atributos:
        product (ForeignKey): Identificador del Producto.
        batch_code (CharField): Código del Lote (si corresponde).
        expiry_date (DateField): Fecha de vencimiento del lote (si corresponde).
        from_location (ForeignKey): Identificador del depósito de donde se extrae el inventario.
        to_location (ForeignKey): Identificador del depósito a donde se transfiere productos.
        quantity (PositiveIntegerField): Cantidad de productos.
        reason (CharField): Razón por la cual se mueve un producto (PURCHASE_ENTRY, EXIT_SALE, TRANSFER, ADJUSTMENT, RETURN_ENTRY, RETURN_OUTPUT)
        description (TextField): Descripción del motivo del movimiento.
        reference_type (CharField): Referencia del movimiento, de que tipo fué (PURCHASE, PAY, MANUAL, SALE).
        reference_id (IntegerField): Identificador del movimiento justificado, ej: compra, pago, etc.
        occurred_at (DateTime): Fecha y Hora en que se realizó el movimiento.
        updated_by (ForeignKey): Referencia al usuario que actualizo el registro.
        created_by (ForeignKey): Referencia al usuario que actualizo el registro.
        updated_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue modificado el registro.
        created_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue creado el registro.
    """
    class Reason(models.TextChoices):
        PURCHASE_ENTRY = "PURCHASE_ENTRY", "PURCHASE_ENTRY"
        EXIT_SALE = "EXIT_SALE", "EXIT_SALE"
        TRANSFER = "TRANSFER", "TRANSFER"
        ADJUSTMENT = "ADJUSTMENT", "ADJUSTMENT"
        RETURN_ENTRY = "RETURN_ENTRY", "RETURN_ENTRY"
        RETURN_OUTPUT = "RETURN_OUTPUT", "RETURN_OUTPUT"

    class RefType(models.TextChoices):
        PURCHASE = "PURCHASE", "PURCHASE"
        PAYMENT = "PAYMENT", "PAYMENT"
        MANUAL = "MANUAL", "MANUAL"
        SALE = "SALE", "SALE"

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    batch_code = models.CharField(max_length=120, null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    from_location = models.ForeignKey(StorageLocation, on_delete=models.CASCADE,
                                      null=True, blank=True, related_name="movements_from")
    to_location = models.ForeignKey(StorageLocation, on_delete=models.CASCADE,
                                    null=True, blank=True, related_name="movements_to")
    quantity = models.PositiveIntegerField()
    reason = models.CharField(max_length=20, choices=Reason.choices)
    description = models.TextField(null=False, blank=True)
    reference_type = models.CharField(max_length=20, choices=RefType.choices)
    reference_id = models.IntegerField(null=True, blank=True)

    occurred_at = models.DateTimeField(
        auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="inventory_movements_created")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="inventory_movements_updated")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['product'], name='idx_im_product'),
            models.Index(fields=['occurred_at'], name='idx_im_occurred'),
            models.Index(fields=['from_location'], name='idx_im_from'),
            models.Index(fields=['to_location'], name='idx_im_to'),
            models.Index(fields=['reference_type',
                         'reference_id'], name='idx_im_ref'),
        ]
        verbose_name = "Movimiento de Inventario"
        verbose_name_plural = "Movimientos de Inventario"


class StockSnapshot(models.Model):
    """
        Modelo materialización para reportes

        Atributos:
            product (ForeignKey): Identificador del Producto.
            location (ForeignKey): Identificador del Depósito.
            batch_code (CharField): Código del Lote (si corresponde).
            expiry_date (DateField): Fecha de vencimiento del lote (si corresponde).
            quantity (PositiveIntegerField): Cantidad de productos.
            last_movement_at (DateTimeField): Fecha y hora del último movimiento.
            updated_by (ForeignKey): Referencia al usuario que actualizo el registro.
            updated_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue modificado el registro.
            created_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue creado el registro.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    location = models.ForeignKey(StorageLocation, on_delete=models.CASCADE)
    batch_code = models.CharField(max_length=120, null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    quantity = models.PositiveIntegerField()
    last_movement_at = models.DateTimeField(
        null=True, blank=True)  # set por proceso

    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="stock_snapshots_updated")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=['product', 'location', 'batch_code', 'expiry_date'], name='uq_snapshot')]
        indexes = [
            models.Index(fields=['product'], name='idx_snapshot_product'),
            models.Index(fields=['location'], name='idx_snapshot_location'),
        ]
        verbose_name = "Materialización reporte"
        verbose_name_plural = "Materialización reportes"
