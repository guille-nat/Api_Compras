from django.db import models
from django.conf import settings
from api.categories.models import Category
from api.products.models import Product
from api.storage_location.models import StorageLocation


class Promotion(models.Model):
    """
    Modelo que gestiona las Promociones

    Atributos:
        name (CharField): Nombre por el cual se identifica la promoción.
        active (BooleanField): Estado de la promoción, indica si esta activado (True) o no (False).
        updated_by (ForeignKey): Referencia al usuario que actualizo el registro.
        created_by (ForeignKey): Referencia al usuario que actualizo el registro.
        updated_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue modificado el registro.
        created_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue creado el registro.
    """
    name = models.CharField(max_length=180, null=False,
                            help_text='Nombre de la promoción.')
    active = models.BooleanField(
        default=False, null=False, help_text='Estado de la promoción.')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="promotion_created"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="promotion_updated"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Promoción"
        verbose_name_plural = "Promociones"
        indexes = [
            models.Index(fields=['active'], name='idx_promotion_active')
        ]


class PromotionScopeCategory(models.Model):
    """
    Modelo que gestiona las Promociones de Categorías

    Atributos:
        promotion (ForeignKey): Referencia a la promoción que aplica.
        category (ForeignKey): Referencia a la categoría que se le aplica la promoción.
        updated_by (ForeignKey): Referencia al usuario que actualizo el registro.
        created_by (ForeignKey): Referencia al usuario que actualizo el registro.
        updated_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue modificado el registro.
        created_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue creado el registro.
    """
    promotion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE, help_text='Identificador de la promoción.')
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, help_text='Identificador de la categoría')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="promotion_category_created"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="promotion_category_updated"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Promoción por Categoría"
        verbose_name_plural = "Promoción por Categorías"
        indexes = [
            models.Index(fields=['category'], name='idx_psc_category'),
            models.Index(fields=['promotion'], name='idx_psc_promotion')
        ]


class PromotionScopeProduct(models.Model):
    """
    Modelo que gestiona las Promociones de Productos

    Atributos:
        promotion (ForeignKey): Referencia a la promoción que aplica.
        product (ForeignKey): Referencia al producto que se le aplica la promoción.
        updated_by (ForeignKey): Referencia al usuario que actualizo el registro.
        created_by (ForeignKey): Referencia al usuario que actualizo el registro.
        updated_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue modificado el registro.
        created_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue creado el registro.
    """
    promotion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE, help_text='Identificador de la promoción.')
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, help_text='Identificador del producto.')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="promotion_product_created"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="promotion_product_updated"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Promoción por Producto"
        verbose_name_plural = "Promoción por Productos"
        indexes = [
            models.Index(fields=['product'], name='idx_psp_product'),
            models.Index(fields=['promotion'], name='idx_psp_promotion')
        ]


class PromotionScopeLocation(models.Model):
    """
    Modelo que gestiona las Promociones por Localización del almacén

    Atributos:
        promotion (ForeignKey): Referencia a la promoción que aplica.
        location (ForeignKey): Referencia a la localización del almacén que se le aplica la promoción.
        updated_by (ForeignKey): Referencia al usuario que actualizo el registro.
        created_by (ForeignKey): Referencia al usuario que actualizo el registro.
        updated_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue modificado el registro.
        created_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue creado el registro.
    """
    promotion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE, help_text='Identificador de la promoción.')
    location = models.ForeignKey(
        StorageLocation, on_delete=models.CASCADE, help_text='Identificador de la localización')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="promotion_location_created"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="promotion_location_updated"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Promoción por Localización"
        verbose_name_plural = "Promoción por Localizaciones"
        indexes = [
            models.Index(fields=['location'], name='idx_psl_location'),
            models.Index(fields=['promotion'], name='idx_psl_promotion')
        ]


class PromotionRule(models.Model):
    """
    Modelo para gestionar las reglas de las promociones.

    Atributos:
        promotion (ForeignKey): Referencia a la promoción que aplica.
        type (CharField): Tipo de regla que se le aplica a la promoción (PERCENTAGE, AMOUNT, FIRST_PURCHASE) 
            [solo a PERCENTAGE se tratara el value como un porcentaje, el resto se tomara como un monto fijo de descuento].
        value (DecimalFile): Valor de descuento que se aplica.
        priority (PositiveIntegerField): Valor de prioridad, mientras más alto el valor mayor prioridad posee.
        start_at (DateTimeField): Fecha y hora en la que comienza la promoción.
        end_at (DateTimeField): Fecha y hora en la que termina la promoción.
        acumulable (BooleanField): Indica si la promoción es acumulable con otras promociones.
        updated_by (ForeignKey): Referencia al usuario que actualizo el registro.
        created_by (ForeignKey): Referencia al usuario que actualizo el registro.
        updated_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue modificado el registro.
        created_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue creado el registro.
    """
    class Type(models.TextChoices):
        PERCENTAGE = "PERCENTAGE", "PERCENTAGE"
        AMOUNT = "AMOUNT", "AMOUNT"
        FIRST_PURCHASE = "FIRST_PURCHASE", "FIRST_PURCHASE"

    promotion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE, help_text='Identificador de la promoción.')
    type = models.CharField(max_length=20, choices=Type.choices, null=False,
                            help_text='Tipo de regla.')
    value = models.DecimalField(max_digits=12, decimal_places=2,
                                null=False, help_text='Valor que se le aplica al descuento.')
    priority = models.PositiveIntegerField(
        default=100, null=False, help_text='Prioridad que se le aplica al descuento.')
    start_at = models.DateTimeField(
        null=False, help_text='Fecha y hora que empieza la promoción.')
    end_at = models.DateTimeField(
        null=False, help_text='Fecha en la que termina la promoción.')
    acumulable = models.BooleanField(
        default=False, null=False, help_text='Indica si la promoción es acumulable con otras promociones.')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="promotion_rule_created"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="promotion_rule_updated"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Regla de Promoción"
        verbose_name_plural = "Reglas de Promociones"
        indexes = [
            models.Index(fields=['promotion'], name='idx_pr_promo'),
            models.Index(fields=['priority'], name='idx_pr_priority'),
            models.Index(fields=['start_at', 'end_at'], name='idx_pr_range')
        ]
