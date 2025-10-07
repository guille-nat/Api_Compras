"""Middleware de manejo seguro de errores.

Oculta información sensible, registra errores y retorna respuestas seguras al cliente.
"""

import logging
import traceback
import json
from datetime import datetime
from django.http import JsonResponse
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response


logger = logging.getLogger(__name__)


class SecureErrorMiddleware:
    """Captura excepciones no manejadas y retorna respuestas seguras.

    Evita exponer información sensible al cliente.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """
        Procesa excepciones no manejadas de forma segura.

        Args:
            request: El objeto request de Django
            exception: La excepción que ocurrió

        Returns:
            JsonResponse: Respuesta segura sin información sensible
        """

    # Registrar el error completo en los logs del servidor
        logger.error(
            f"Error no manejado en {request.path}: {str(exception)}",
            exc_info=True,
            extra={
                'request_path': request.path,
                'request_method': request.method,
                'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                'user_email': getattr(request.user, 'email', None) if hasattr(request, 'user') else None,
                'exception_type': type(exception).__name__,
                'exception_args': str(exception.args),
                'full_traceback': traceback.format_exc()
            }
        )

    # Determinar tipo de error y respuesta apropiada
        error_type = type(exception).__name__

        if error_type == 'AssertionError':
            if 'Expected a `Response`' in str(exception):
                error_msg = "Error interno del servidor. El formato de respuesta es inválido."
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            else:
                error_msg = "Error de validación interna."
                status_code = status.HTTP_400_BAD_REQUEST

        elif error_type in ['ValueError', 'TypeError']:
            error_msg = "Error de validación en los datos proporcionados."
            status_code = status.HTTP_400_BAD_REQUEST

        elif error_type == 'PermissionDenied':
            error_msg = "No tiene permisos para realizar esta acción."
            status_code = status.HTTP_403_FORBIDDEN

        elif error_type in ['DoesNotExist', 'Http404']:
            error_msg = "El recurso solicitado no fue encontrado."
            status_code = status.HTTP_404_NOT_FOUND

        else:
            error_msg = "Error interno del servidor. Contacte al administrador."
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    # Crear respuesta segura
        safe_response = {
            "error": True,
            "message": error_msg,
            "error_code": error_type,
            "timestamp": datetime.now().isoformat(),
            "path": request.path,
            "method": request.method
        }

        # Solo incluir información adicional si DEBUG está activado en entorno de desarrollo
        if settings.DEBUG and settings.DEBUG:  # Doble verificación intencional
            safe_response["debug_info"] = {
                "exception_type": error_type,
                "exception_message": str(exception),
                # NO incluir traceback completo por seguridad
            }

        return JsonResponse(
            safe_response,
            status=status_code,
            safe=False
        )


class SecureDebugMiddleware:
    """Filtra respuestas de error para evitar exponer información sensible."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Filtrar respuestas de error que podrían contener información sensible
        if (hasattr(response, 'status_code') and
            response.status_code >= 400 and
                hasattr(response, 'content')):

            try:
                # Verificar si el contenido contiene información sensible
                content_str = response.content.decode('utf-8')

                # Lista de patrones sensibles que no deben exponerse
                sensitive_patterns = [
                    'SECRET_KEY',
                    'PASSWORD',
                    'DJANGO_SUPERUSER_PASSWORD',
                    'EMAIL_HOST_PASSWORD',
                    'REDIS_PASSWORD',
                    'MYSQL_PASSWORD',
                    'JWT_SECRET',
                    'DATABASE_URL',
                    '/usr/local/lib/python',
                    'django.core.handlers',
                    'wsgi.errors',
                    'META:',
                    'Settings:',
                    'DATABASES = {',
                ]

                contains_sensitive = any(
                    pattern in content_str for pattern in sensitive_patterns)

                if contains_sensitive:
                    # Registrar la respuesta original en los logs
                    logger.warning(
                        f"Respuesta con información sensible interceptada en {request.path}",
                        extra={
                            'status_code': response.status_code,
                            'content_length': len(content_str),
                            'has_sensitive_data': True
                        }
                    )

                    # Reemplazar con respuesta segura
                    safe_content = {
                        "error": True,
                        "message": "Error interno del servidor. Contacte al administrador.",
                        "error_code": "INTERNAL_SERVER_ERROR",
                        "status_code": response.status_code,
                        "timestamp": datetime.now().isoformat(),
                        "path": request.path,
                        "method": request.method,
                        "note": "Error details have been logged for security purposes."
                    }

                    response.content = json.dumps(
                        safe_content, indent=2).encode('utf-8')
                    response['Content-Type'] = 'application/json'

            except UnicodeDecodeError:
                # Si no se puede decodificar, es mejor ser conservador
                pass
            except Exception as e:
                # Si hay algún error procesando, no romper la respuesta original
                logger.error(f"Error en SecureDebugMiddleware: {str(e)}")

        return response
