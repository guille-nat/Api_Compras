"""
Funciones helper para respuestas estándar de la API.

Este módulo centraliza la creación de respuestas siguiendo el estándar definido
en response_standards.md para mantener consistencia en toda la API.

Estructura estándar:
{
    "success": true/false,
    "message": "Mensaje descriptivo", 
    "data": {...} // Datos específicos (opcional)
}
"""

from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response


def success_response(message: str, data=None, status_code=status.HTTP_200_OK):
    """
    Crea una respuesta de éxito estándar.

    Args:
        message (str): Mensaje descriptivo del éxito
        data: Datos a incluir en la respuesta (opcional)
        status_code (int): Código de estado HTTP (default: 200)

    Returns:
        JsonResponse: Respuesta formateada con estructura estándar

    Example:
        return success_response("Producto creado exitosamente", {"id": 1, "name": "Producto"})
    """
    response_data = {
        "success": True,
        "message": message,
        "data": data
    }
    return JsonResponse(response_data, status=status_code)


def error_response(message: str, data=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Crea una respuesta de error estándar.

    Args:
        message (str): Mensaje descriptivo del error
        data: Datos adicionales del error (opcional)
        status_code (int): Código de estado HTTP (default: 400)

    Returns:
        JsonResponse: Respuesta formateada con estructura estándar

    Example:
        return error_response("Parámetro requerido faltante", status_code=400)
    """
    response_data = {
        "success": False,
        "message": message,
        "data": data
    }
    return JsonResponse(response_data, status=status_code)


def validation_error_response(message: str, data=None):
    """
    Crea una respuesta de error de validación.

    Args:
        message (str): Mensaje descriptivo del error de validación
        data: Datos adicionales del error (opcional)

    Returns:
        JsonResponse: Respuesta formateada con código 400
    """
    return error_response(message, data, status.HTTP_400_BAD_REQUEST)


def server_error_response(message: str, data=None):
    """
    Crea una respuesta de error interno del servidor.

    Args:
        message (str): Mensaje descriptivo del error interno
        data: Datos adicionales del error (opcional)

    Returns:
        JsonResponse: Respuesta formateada con código 500
    """
    return error_response(message, data, status.HTTP_500_INTERNAL_SERVER_ERROR)


def not_found_error_response(message: str, data=None):
    """
    Crea una respuesta de recurso no encontrado.

    Args:
        message (str): Mensaje descriptivo del recurso no encontrado
        data: Datos adicionales del error (opcional)

    Returns:
        JsonResponse: Respuesta formateada con código 404
    """
    return error_response(message, data, status.HTTP_404_NOT_FOUND)


def date_validation_error_response(param_name: str = "from_date"):
    """
    Crea una respuesta de error para formato de fecha inválido.

    Args:
        param_name (str): Nombre del parámetro de fecha (default: "from_date")

    Returns:
        JsonResponse: Respuesta formateada con mensaje específico de fecha
    """
    message = f"El parámetro '{param_name}' debe tener formato YYYY-MM-DD."
    return validation_error_response(message)


def required_param_error_response(param_name: str = "from_date"):
    """
    Crea una respuesta de error para parámetro requerido faltante.

    Args:
        param_name (str): Nombre del parámetro requerido (default: "from_date")

    Returns:
        JsonResponse: Respuesta formateada con mensaje específico de parámetro requerido
    """
    message = f"El parámetro '{param_name}' es requerido."
    return validation_error_response(message)
