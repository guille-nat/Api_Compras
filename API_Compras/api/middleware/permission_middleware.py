"""
Middleware para manejo centralizado de errores de permisos.

Intercepta excepciones de permisos no manejadas y las convierte
en respuestas JSON estructuradas y amigables para el usuario.
"""

import json
import logging
from django.http import JsonResponse
from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from api.permissions import PermissionDenied

logger = logging.getLogger(__name__)


class PermissionErrorMiddleware:
    """
    Middleware que intercepta errores de permisos y devuelve respuestas estructuradas.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """
        Procesa excepciones de permisos no manejadas.

        Args:
            request: HttpRequest object
            exception: Exception raised

        Returns:
            JsonResponse with structured error or None to continue normal handling
        """

        # Manejar PermissionDenied de Django REST Framework
        if isinstance(exception, DRFPermissionDenied):
            logger.warning(
                f"DRF Permission denied for user {getattr(request.user, 'username', 'anonymous')} on {request.path}")

            # Intentar determinar el tipo de error basado en la URL
            if '/analytics/' in request.path or '/admin/' in request.path:
                error_response = PermissionDenied.admin_required(
                    'access_analytics')
            elif '/purchases/' in request.path:
                error_response = PermissionDenied.purchase_access_denied(
                    getattr(request.user, 'id', 0),
                    None,
                    'access'
                )
            else:
                error_response = {
                    "success": False,
                    "message": "No tienes permisos para realizar esta acción.",
                    "data": {
                        "error_type": "permission_denied",
                        "detail": str(exception)
                    }
                }

            return JsonResponse(error_response, status=403)

        # Manejar PermissionDenied de Django
        if isinstance(exception, DjangoPermissionDenied):
            logger.warning(
                f"Django Permission denied for user {getattr(request.user, 'username', 'anonymous')} on {request.path}")

            error_response = {
                "success": False,
                "message": "No tienes permisos para realizar esta acción.",
                "data": {
                    "error_type": "permission_denied",
                    "detail": str(exception)
                }
            }

            return JsonResponse(error_response, status=403)

        # Manejar PermissionError de Python
        if isinstance(exception, PermissionError):
            logger.warning(
                f"Permission error for user {getattr(request.user, 'username', 'anonymous')} on {request.path}: {str(exception)}")

            # Intentar parsear el mensaje para crear respuesta específica
            error_message = str(exception).lower()

            if "only staff users" in error_message or "only administrators" in error_message:
                if "delete" in error_message:
                    error_response = PermissionDenied.admin_required(
                        'delete_purchase')
                elif "cancel" in error_message and "paid" in error_message:
                    error_response = PermissionDenied.admin_required(
                        'cancel_paid')
                elif "reactivate" in error_message:
                    error_response = PermissionDenied.admin_required(
                        'reactivate_cancelled')
                else:
                    error_response = PermissionDenied.admin_required(
                        'access_admin_function')
            elif "only update your own" in error_message:
                error_response = PermissionDenied.purchase_access_denied(
                    getattr(request.user, 'id', 0),
                    None,
                    'modify'
                )
            else:
                error_response = {
                    "success": False,
                    "message": str(exception),
                    "data": {
                        "error_type": "permission_denied"
                    }
                }

            return JsonResponse(error_response, status=403)

        # No manejar esta excepción, continuar con el procesamiento normal
        return None
