from django.db import models
from django.conf import settings


class StorageLocation(models.Model):
    """
    Modelo para representar los Depósitos y jerarquía (almacén → subalmacén → estante …)

    Atributos:
        name (CharField): Nombre por el cual se reconoce al depósito.
        street (CharField): Calle en la cual está ubicado el depósito.
        street_number (CharField): Altura exacta en donde está ubicado el depósito, ej: 1233.
        floor_unit (CharField): Número de piso y sección en donde está ubicado, ej: 12-E.
        state (CharField): Estado/Provincia en donde está ubicado el depósito.
        city (CharField): Ciudad en donde está ubicado el depósito.
        country (CharField): País en donde está ubicado el depósito.
        type (CharField): Tipo de depósito (WAREHOUSE, SUBWAREHOUSE, SHELF, OTHER).
        parent (ForeignKey): Referencia al registro padre (si corresponde).
        updated_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue modificado el registro.
        created_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue creado el registro.
        updated_by (ForeignKey): Referencia al usuario que actualizo el registro.
        created_by (ForeignKey): Referencia al usuario que actualizo el registro.
    """
    TYPE = [
        ('WH', 'WAREHOUSE'),
        ('SB', 'SUBWAREHOUSE'),
        ('SH', 'SHELF'),
        ('OT', 'OTHER'),
    ]

    name = models.CharField(max_length=180, help_text='Nombre del depósito.')
    street = models.CharField(
        max_length=255, null=False, help_text='Calle (ej: Av. Corrientes).')
    street_number = models.CharField(
        max_length=10, null=False, help_text='Altura (ej: 1543).')
    floor_unit = models.CharField(
        max_length=10, null=True, blank=True, help_text='Piso/unidad (si aplica).')
    state = models.CharField(max_length=120, null=False,
                             help_text='Provincia/estado.')
    city = models.CharField(max_length=120, null=False, help_text='Ciudad.')
    country = models.CharField(max_length=120, null=False, help_text='País.')
    type = models.CharField(max_length=2, choices=TYPE,
                            default='WH', null=False)

    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='children',
        help_text='Nodo padre en la jerarquía.'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="storage_locations_created"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="storage_locations_updated"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Depósito"
        verbose_name_plural = "Depósitos"
        constraints = [
            # Igual que UNIQUE(parent_id, type, name) en el SQL
            models.UniqueConstraint(
                fields=['parent', 'type', 'name'], name='uq_location'),
        ]
        indexes = [
            models.Index(fields=['parent'], name='idx_location_parent'),
            models.Index(fields=['type'], name='idx_location_type'),
            models.Index(fields=['name'], name='idx_location_name'),
        ]
        ordering = ['name']

    def __str__(self):
        return f"{self.name} [{self.get_type_display()}]"

    def clean(self):
        # Guardrail mínimo: no permitas que el padre sea uno mismo
        if self.parent_id and self.parent_id == self.pk:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                "El depósito no puede ser padre de sí mismo.")
