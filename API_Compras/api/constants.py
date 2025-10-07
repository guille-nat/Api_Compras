"""
Constantes del sistema de compras.

Este módulo centraliza todas las constantes utilizadas en el sistema,
proporcionando un punto único de verdad para valores que se utilizan
en múltiples módulos.
"""

from django.db import models


class NotificationCodes:
    """
    Códigos de notificaciones disponibles en el sistema.

    Esta clase centraliza todos los códigos de templates de notificación
    que pueden ser utilizados por el sistema para evitar hardcodeo y
    facilitar el mantenimiento.

    Uso:
        from api.constants import NotificationCodes

        # En lugar de: 'installment_paid'
        # Usar: NotificationCodes.INSTALLMENT_PAID
    """

    # Códigos de templates de notificación
    PURCHASE_CONFIRMED = "purchase_confirmed"
    INSTALLMENT_DUE_7D = "installment_due_7d"
    INSTALLMENT_PAID = "installment_paid"
    PAYMENT_ERROR = "payment_error"
    OVERDUE_NOTICE = "overdue_notice"
    OVERDUE_SURCHARGE_NOTICE = "overdue_surcharge_notice"
    CREATED_ACCOUNT = "created_account"
    UPDATED_ACCOUNT = "updated_account"

    # Lista de todos los códigos para validación
    ALL_CODES = [
        PURCHASE_CONFIRMED,
        INSTALLMENT_DUE_7D,
        INSTALLMENT_PAID,
        PAYMENT_ERROR,
        OVERDUE_NOTICE,
        OVERDUE_SURCHARGE_NOTICE,
        CREATED_ACCOUNT,
        UPDATED_ACCOUNT,
    ]

    @classmethod
    def get_choices(cls):
        """
        Retorna las opciones para usar en Django choices.

        Returns:
            list: Lista de tuplas (valor, etiqueta) para usar en choices
        """
        return [
            (cls.PURCHASE_CONFIRMED, "Compra Confirmada"),
            (cls.INSTALLMENT_DUE_7D, "Cuota Vence en 7 Días"),
            (cls.INSTALLMENT_PAID, "Cuota Pagada"),
            (cls.PAYMENT_ERROR, "Error en Pago"),
            (cls.OVERDUE_NOTICE, "Aviso de Vencimiento"),
            (cls.OVERDUE_SURCHARGE_NOTICE, "Aviso de Recargo por Vencimiento"),
            (cls.CREATED_ACCOUNT, "Cuenta Creada"),
            (cls.UPDATED_ACCOUNT, "Cuenta Actualizada"),
        ]

    @classmethod
    def is_valid_code(cls, code: str) -> bool:
        """
        Valida si un código es válido.

        Args:
            code (str): Código a validar

        Returns:
            bool: True si el código es válido, False en caso contrario
        """
        return code in cls.ALL_CODES


class EmailSettings:
    """
    Configuraciones relacionadas con el envío de emails.
    """

    # Límites de longitud
    MAX_SUBJECT_LENGTH = 180
    MAX_EMAIL_LENGTH = 255
    MAX_ERROR_MESSAGE_LENGTH = 255

    # Templates por defecto
    DEFAULT_FROM_EMAIL = "noreply@sistemacompras.com"

    # Timeout para envío de emails (segundos)
    EMAIL_TIMEOUT = 30


class AuditFields:
    """
    Constantes para campos de auditoría comunes.
    """

    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    CREATED_BY = "created_by"
    UPDATED_BY = "updated_by"

    # Nombres de índices comunes
    INDEX_CREATED_AT = "idx_{}_created"
    INDEX_UPDATED_AT = "idx_{}_updated"
    INDEX_USER = "idx_{}_user"
