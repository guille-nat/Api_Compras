"""
Middleware para manejo centralizado de errores 404.

Intercepta respuestas 404 y las convierte en respuestas JSON estructuradas
siguiendo los estándares del proyecto.
"""

import json
import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class NotFoundErrorMiddleware(MiddlewareMixin):
    """
    Middleware que intercepta respuestas 404 y devuelve respuestas JSON estructuradas.

    Este middleware se ejecuta después de que Django determina que no hay una URL
    que coincida con la solicitud. Convierte la respuesta 404 HTML estándar en
    una respuesta JSON que sigue los estándares del proyecto.
    """

    def process_response(self, request, response):
        """
        Procesa las respuestas 404 y las convierte en JSON estructurado.

        Args:
            request: HttpRequest object
            response: HttpResponse object with status 404

        Returns:
            JsonResponse with structured error for 404 or original response
        """

        # Solo procesar respuestas 404
        if response.status_code == 404:
            # Verificar si ya es una respuesta JSON válida (viene de nuestros servicios)
            if self._is_json_response(response):
                # Ya es una respuesta JSON estructurada, no la modificamos
                return response

            # Verificar si es una solicitud a la API (para evitar interferir con admin, static files, etc.)
            if self._is_api_request(request):
                # Obtener el nombre del usuario de forma segura
                user_info = 'anonymous'
                if hasattr(request, 'user') and hasattr(request.user, 'username'):
                    user_info = request.user.username
                elif hasattr(request, 'user') and hasattr(request.user, 'is_anonymous'):
                    user_info = 'anonymous' if request.user.is_anonymous else str(
                        request.user)

                logger.info(
                    f"404 error for API endpoint: {request.method} {request.path} - "
                    f"User: {user_info}"
                )

                return self._create_404_response(request)

        return response

    def _is_json_response(self, response):
        """
        Verifica si la respuesta ya es una respuesta JSON válida.

        Args:
            response: HttpResponse object

        Returns:
            bool: True si es una respuesta JSON válida, False en caso contrario
        """
        # Verificar el Content-Type
        content_type = response.get('Content-Type', '')
        if 'application/json' in content_type:
            return True

        # Verificar si el contenido es JSON válido
        try:
            content = response.content.decode('utf-8')
            parsed = json.loads(content)
            # Verificar si tiene la estructura estándar de nuestros servicios
            return isinstance(parsed, dict) and ('success' in parsed or 'message' in parsed)
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            return False

    def _is_api_request(self, request):
        """
        Determina si la solicitud es para un endpoint de la API.

        Args:
            request: HttpRequest object

        Returns:
            bool: True si es una solicitud API, False en caso contrario
        """
        # Verificar si la ruta comienza con /api/
        if request.path.startswith('/api/'):
            return True

        # Verificar si se solicita JSON en los headers Accept
        accept_header = request.META.get('HTTP_ACCEPT', '')
        if 'application/json' in accept_header:
            return True

        # Verificar si el Content-Type es JSON (para POST/PUT requests)
        content_type = request.META.get('CONTENT_TYPE', '')
        if 'application/json' in content_type:
            return True

        return False

    def _create_404_response(self, request):
        """
        Crea una respuesta JSON estructurada para errores 404.

        Args:
            request: HttpRequest object

        Returns:
            JsonResponse: Respuesta JSON estructurada según los estándares del proyecto
        """
        # Determinar el mensaje específico basado en la URL
        endpoint_path = request.path
        method = request.method

        # Mensajes personalizados para diferentes tipos de endpoints
        if '/api/v2/purchases/' in endpoint_path:
            message = "El endpoint de compras solicitado no existe. Verifica la URL y los parámetros proporcionados."
        elif '/api/v2/products/' in endpoint_path:
            message = "El endpoint de productos solicitado no existe. Verifica la URL y los parámetros proporcionados."
        elif '/api/v2/payments/' in endpoint_path:
            message = "El endpoint de pagos solicitado no existe. Verifica la URL y los parámetros proporcionados."
        elif '/api/v2/users/' in endpoint_path:
            message = "El endpoint de usuarios solicitado no existe. Verifica la URL y los parámetros proporcionados."
        elif '/api/v2/categories/' in endpoint_path:
            message = "El endpoint de categorías solicitado no existe. Verifica la URL y los parámetros proporcionados."
        elif '/api/v2/inventories/' in endpoint_path:
            message = "El endpoint de inventarios solicitado no existe. Verifica la URL y los parámetros proporcionados."
        elif '/api/v2/analytics/' in endpoint_path:
            message = "El endpoint de analíticas solicitado no existe. Verifica la URL y los parámetros proporcionados."
        elif '/api/v2/promotions/' in endpoint_path:
            message = "El endpoint de promociones solicitado no existe. Verifica la URL y los parámetros proporcionados."
        elif '/api/v2/' in endpoint_path:
            message = "El endpoint de la API solicitado no existe. Consulta la documentación para ver los endpoints disponibles."
        else:
            message = "El recurso solicitado no fue encontrado. Verifica la URL y consulta la documentación de la API."

        response_data = {
            "success": False,
            "message": message,
            "data": {
                "error_type": "endpoint_not_found",
                "requested_path": endpoint_path,
                "method": method,
                "available_versions": ["v2"],
                "documentation_url": "/api/v2/schema/swagger-ui/",
                "suggestions": self._get_endpoint_suggestions(endpoint_path)
            }
        }

        return JsonResponse(response_data, status=404)

    def _get_endpoint_suggestions(self, path):
        """
        Proporciona sugerencias de endpoints similares basados en la ruta solicitada.

        Args:
            path: String con la ruta solicitada

        Returns:
            list: Lista de sugerencias de endpoints
        """
        suggestions = []

        # Sugerencias basadas en patrones comunes
        if '/api/v1/' in path:
            suggestions.append(
                "Usa /api/v2/ en lugar de /api/v1/ (versión obsoleta)")

        if 'purchase' in path.lower():
            suggestions.extend([
                "/api/v2/purchases/ - Lista de compras",
                "/api/v2/purchases/{id}/ - Detalle de compra específica",
                "/api/v2/purchases/{id}/payments/ - Pagos de una compra"
            ])

        elif 'product' in path.lower():
            suggestions.extend([
                "/api/v2/products/ - Lista de productos",
                "/api/v2/products/{id}/ - Detalle de producto específico"
            ])

        elif 'user' in path.lower():
            suggestions.extend([
                "/api/v2/users/profile/ - Perfil del usuario",
                "/api/v2/users/register/ - Registro de usuario",
                "/api/v2/users/login/ - Inicio de sesión"
            ])

        elif 'payment' in path.lower():
            suggestions.extend([
                "/api/v2/payments/ - Lista de pagos",
                "/api/v2/payments/{id}/ - Detalle de pago específico"
            ])

        else:
            suggestions.extend([
                "/api/v2/purchases/ - Gestión de compras",
                "/api/v2/products/ - Gestión de productos",
                "/api/v2/users/ - Gestión de usuarios",
                "/api/v2/schema/swagger-ui/ - Documentación completa"
            ])

        return suggestions[:3]  # Limitar a 3 sugerencias para no sobrecargar
