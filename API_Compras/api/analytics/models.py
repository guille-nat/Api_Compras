from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Report(models.Model):
    """
    Modelo para almacenar reportes generados de forma asíncrona.

    Attributes:
        user: Usuario que solicitó el reporte
        report_type: Tipo de reporte generado
        status: Estado actual del reporte
        task_id: ID de la tarea de Celery
        file: Archivo del reporte generado
        parameters: Parámetros usados para generar el reporte
        error_message: Mensaje de error si falló la generación
        created_at: Fecha de creación de la solicitud
        completed_at: Fecha de finalización del reporte
    """

    class ReportType(models.TextChoices):
        """Tipos de reportes disponibles."""
        PRODUCT_ROTATION = 'PRODUCT_ROTATION', 'Rotación de Productos'
        MOVEMENTS_INPUT_OUTPUT = 'MOVEMENTS_INPUT_OUTPUT', 'Movimientos Entrada/Salida'
        SALES_SUMMARY = 'SALES_SUMMARY', 'Resumen de Ventas'
        TOP_PRODUCTS = 'TOP_PRODUCTS', 'Productos Más Vendidos'
        PAYMENT_METHODS = 'PAYMENT_METHODS', 'Métodos de Pago'
        OVERDUE_INSTALLMENTS = 'OVERDUE_INSTALLMENTS', 'Cuotas Vencidas'

    class Status(models.TextChoices):
        """Estados posibles del reporte."""
        PENDING = 'PENDING', 'Pendiente'
        PROCESSING = 'PROCESSING', 'Procesando'
        COMPLETED = 'COMPLETED', 'Completado'
        FAILED = 'FAILED', 'Fallido'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name='Usuario'
    )
    report_type = models.CharField(
        max_length=50,
        choices=ReportType.choices,
        verbose_name='Tipo de Reporte'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Estado'
    )
    task_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='ID de Tarea'
    )
    file = models.FileField(
        upload_to='reports/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name='Archivo'
    )
    parameters = models.JSONField(
        default=dict,
        verbose_name='Parámetros'
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name='Mensaje de Error'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Finalización'
    )

    class Meta:
        db_table = 'analytics_reports'
        verbose_name = 'Reporte'
        verbose_name_plural = 'Reportes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['task_id']),
        ]

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.user.username} ({self.status})"
