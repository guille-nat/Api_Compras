"""Paquete de permisos y utilidades de autenticación.

Exporta los decoradores, respuestas y clases de permiso para uso desde
`api.permissions` o `api.permissions.decorators`/`responses`.
"""
from .decorators import admin_required_with_message, ownership_required
from .responses import PermissionDenied, log_permission_attempt
from .permissions import IsAdminUser

__all__ = [
    'admin_required_with_message', 'ownership_required',
    'PermissionDenied', 'log_permission_attempt',
    'IsAdminUser'
]
