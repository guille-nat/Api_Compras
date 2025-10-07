"""Decoradores personalizados para manejo de permisos con respuestas amigables.
"""
from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from api.permissions.responses import PermissionDenied
import logging

logger = logging.getLogger(__name__)


def admin_required_with_message(view_func):
    """
    Decorator que valida permisos de admin y devuelve mensaje amigable si no los tiene.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({
                "success": False,
                "message": "Debes estar autenticado para acceder a esta función.",
                "data": {
                    "error_type": "authentication_required"
                }
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not request.user.is_staff:
            logger.warning(
                f"Access denied - User {request.user.username} (ID: {request.user.id}) attempted to access admin analytics")

            function_name = view_func.__name__
            if 'analytics' in function_name or 'report' in function_name:
                action = 'access_analytics'
            elif 'admin' in function_name:
                action = 'access_admin_panel'
            else:
                action = 'access_admin_function'

            error_response = PermissionDenied.admin_required(action)
            return Response(error_response, status=status.HTTP_403_FORBIDDEN)

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def ownership_required(get_resource_user_id):
    """
    Decorator que valida que el usuario sea dueño del recurso o admin.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return Response({
                    "success": False,
                    "message": "Debes estar autenticado para realizar esta acción.",
                    "data": {
                        "error_type": "authentication_required"
                    }
                }, status=status.HTTP_401_UNAUTHORIZED)

            if request.user.is_staff:
                return view_func(request, *args, **kwargs)

            try:
                resource_user_id = get_resource_user_id(
                    request, *args, **kwargs)

                if request.user.id != resource_user_id:
                    resource_id = kwargs.get('purchase_id') or kwargs.get(
                        'pk') or kwargs.get('id')

                    error_response = PermissionDenied.purchase_access_denied(
                        request.user.id, resource_id, "access"
                    )
                    return Response(error_response, status=status.HTTP_403_FORBIDDEN)

            except Exception as e:
                logger.error(f"Error validating ownership: {str(e)}")
                return Response({
                    "success": False,
                    "message": "Error validando permisos de acceso.",
                    "data": {
                        "error_type": "permission_validation_error"
                    }
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return view_func(request, *args, **kwargs)

        return _wrapped_view
    return decorator
