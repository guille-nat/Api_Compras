"""Módulo de utilidades para manejo de respuestas de error de permisos.
"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class PermissionDenied:
    """
    Clase para generar respuestas estandarizadas de acceso denegado.
    """

    @staticmethod
    def purchase_access_denied(user_id: int, purchase_id: Optional[int], action: str = "access") -> Dict[str, Any]:
        action_messages = {
            'access': 'acceder a',
            'modify': 'modificar',
            'delete': 'eliminar',
            'view': 'ver'
        }

        action_text = action_messages.get(action, action)

        purchase_id_str = purchase_id if purchase_id is not None else 'unknown'
        logger.warning(
            f"Access denied - User ID {user_id} attempted to {action} purchase {purchase_id_str}")

        return {
            "success": False,
            "message": f"No tienes permisos para {action_text} esta compra. Solo puedes {action_text} tus propias compras.",
            "data": {
                "error_type": "access_denied",
                "resource": "purchase",
                "resource_id": purchase_id,
                "action": action,
                "user_id": user_id
            }
        }

    @staticmethod
    def admin_required(action: str, resource: str = "function", current_status: Optional[str] = None) -> Dict[str, Any]:
        action_messages = {
            'cancel_paid': 'cancelar compras que ya han sido pagadas',
            'reactivate_cancelled': 'reactivar compras canceladas',
            'delete_purchase': 'eliminar compras',
            'access_analytics': 'acceder a las analíticas del sistema',
            'manage_users': 'gestionar usuarios',
            'access_admin_panel': 'acceder al panel de administración'
        }

        message = action_messages.get(action, f"realizar la acción '{action}'")
        base_message = f"Esta función requiere permisos de administrador. Solo los administradores pueden {message}."

        logger.warning(
            f"Admin required - Action '{action}' attempted on {resource}")

        response_data = {
            "success": False,
            "message": base_message,
            "data": {
                "error_type": "admin_required",
                "resource": resource,
                "action": action
            }
        }

        if current_status:
            response_data["data"]["current_status"] = current_status

        return response_data

    @staticmethod
    def resource_not_found(resource_type: str, resource_id: int) -> Dict[str, Any]:
        resource_messages = {
            'purchase': 'La compra solicitada no existe o ha sido eliminada.',
            'user': 'El usuario especificado no existe.',
            'product': 'El producto especificado no existe.',
            'category': 'La categoría especificada no existe.'
        }

        message = resource_messages.get(
            resource_type, f"El recurso {resource_type} no existe.")

        logger.info(
            f"Resource not found - {resource_type} with ID {resource_id}")

        return {
            "success": False,
            "message": message,
            "data": {
                "error_type": "not_found",
                "resource": resource_type,
                "resource_id": resource_id
            }
        }

    @staticmethod
    def invalid_transition(current_status: str, requested_status: str, allowed_transitions: list) -> Dict[str, Any]:
        logger.warning(
            f"Invalid transition - From {current_status} to {requested_status}")

        return {
            "success": False,
            "message": f"No se puede cambiar el estado de {current_status} a {requested_status}. Las transiciones válidas son: {allowed_transitions}",
            "data": {
                "error_type": "invalid_transition",
                "current_status": current_status,
                "requested_status": requested_status,
                "allowed_transitions": allowed_transitions
            }
        }

    @staticmethod
    def validation_error(message: str, invalid_fields: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        response_data = {
            "success": False,
            "message": message,
            "data": {
                "error_type": "validation_error"
            }
        }

        if invalid_fields:
            response_data["data"]["invalid_fields"] = list(
                invalid_fields.keys())
            response_data["data"]["details"] = invalid_fields

        return response_data


def log_permission_attempt(user_id: int, username: str, action: str, resource: str, resource_id: Optional[int] = None):
    resource_info = f"{resource} {resource_id}" if resource_id else resource
    logger.warning(
        f"Access denied - User {username} (ID: {user_id}) attempted to {action} {resource_info}")
