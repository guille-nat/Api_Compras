from django.db import models
from django.conf import settings


class NotificationTemplate(models.Model):
    """
    Modelo para gestionar los templates de las notificaciones.

    Atributos:
        code (CharField): Código de la notificación identificadora. 
            (purchase_confirmed | installment_due_7d | installment_paid | payment_error | overdue_notice)
        subject (CharField):  Asunto del envió de la notificación.
        body_html (CharField): Cuerpo del HTML con estilos que se enviará.
        active (BooleanField): Estado del template. activado(True), desactivado(False).
        updated_by (ForeignKey): Referencia al usuario que actualizo el registro.
        created_by (ForeignKey): Referencia al usuario que actualizo el registro.
        updated_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue modificado el registro.
        created_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue creado el registro.
    """
    # purchase_confirmed | installment_due_7d | installment_paid | payment_error | overdue_notice
    code = models.CharField(max_length=100, null=False,
                            help_text="Código de template.", unique=True)
    subject = models.CharField(max_length=180, null=False, help_text="Asunto.")
    body_html = models.TextField(null=False, help_text="Cuerpo del HTML.")
    active = models.BooleanField(
        default=True, null=False, help_text="Estado del template.")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="notification_template_created"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="notification_template_updated"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Plantilla de Notificación"
        verbose_name_plural = "Plantillas de Notificaciones"
        constraints = [
            models.UniqueConstraint(fields=['code'], name='uq_nt_code')
        ]


class NotificationLog(models.Model):
    class Status(models.TextChoices):
        SENT = "SENT", "SENT"
        ERROR = "ERROR", "ERROR"
    """
    Modelo para gestionar los Logs de las notificaciones

    Atributos:
        user (ForeignKey): Referencia al usuario.
        template (CharField):  Código de la notificación identificadora. 
            (purchase_confirmed | installment_due_7d | installment_paid | payment_error | overdue_notice)
        context_json (JSONField): JSON que representa al contexto del Log.
        recipient_email (CharField): Contenido del email que se envió.
        sent_at (DateTimeField): Fecha y hora en la que se envió el email. 
        status (CharField): Estado en que se encuentra el email (SENT, ERROR).
        error_message (CharField): Mensaje de error si es que corresponde.
        updated_by (ForeignKey): Referencia al usuario que actualizo el registro.
        created_by (ForeignKey): Referencia al usuario que actualizo el registro.
        updated_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue modificado el registro.
        created_at (DateTimeField): Campo de auditoría almacena la fecha y hora que fue creado el registro.
    """
    STATUS = [
        ('ST', 'SENT'),
        ('ER', 'ERROR')
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE,
                             help_text='Usuario destinatario.')

    # FK al campo code de NotificationTemplate
    template = models.ForeignKey(
        NotificationTemplate,
        to_field="code",
        db_column="template_code",
        on_delete=models.SET_NULL,     # para no romper históricos si borrás templates
        null=True, blank=True,
        help_text="Código de template usado."
    )

    context_json = models.JSONField(
        null=True, blank=True, help_text='Payload dinámico.')
    recipient_email = models.CharField(max_length=255, null=False)
    # se setea cuando realmente se envía
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10,
                              choices=Status.choices,
                              default=Status.SENT)
    error_message = models.CharField(max_length=255, null=True, blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="notification_logs_created")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="notification_logs_updated")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Log de Notificación"
        verbose_name_plural = "Logs de Notificaciones"
        indexes = [
            models.Index(fields=['user'], name='idx_nl_user'),
            models.Index(fields=['status'], name='idx_nl_status'),
            models.Index(fields=['sent_at'], name='idx_nl_sent'),
            models.Index(fields=['template'], name='idx_nl_tpl'),
        ]
