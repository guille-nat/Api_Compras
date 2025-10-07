"""
Test básico para verificar las funciones de PermissionDenied sin base de datos.
"""

import unittest
from api.permissions import PermissionDenied


class BasicPermissionResponsesTest(unittest.TestCase):
    """Test cases básicos para validar respuestas de permisos sin DB."""

    def test_permission_denied_structure(self):
        """Test que las respuestas de PermissionDenied tengan la estructura correcta."""
        response = PermissionDenied.purchase_access_denied(1, 123, "view")

        # Verificar estructura básica
        self.assertIn('success', response)
        self.assertIn('message', response)
        self.assertIn('data', response)
        self.assertFalse(response['success'])

        # Verificar data contiene campos requeridos
        data = response['data']
        self.assertIn('error_type', data)
        self.assertIn('resource', data)
        self.assertIn('action', data)
        self.assertEqual(data['error_type'], 'access_denied')

    def test_admin_required_structure(self):
        """Test que respuestas admin_required tengan estructura correcta."""
        response = PermissionDenied.admin_required("delete_purchase")

        self.assertIn('success', response)
        self.assertIn('message', response)
        self.assertIn('data', response)
        self.assertFalse(response['success'])

        data = response['data']
        self.assertEqual(data['error_type'], 'admin_required')
        self.assertIn('action', data)

    def test_resource_not_found_structure(self):
        """Test estructura de respuesta para recurso no encontrado."""
        response = PermissionDenied.resource_not_found("purchase", 99999)

        self.assertFalse(response['success'])
        self.assertIn('no existe', response['message'])

        data = response['data']
        self.assertEqual(data['error_type'], 'not_found')
        self.assertEqual(data['resource'], 'purchase')
        self.assertEqual(data['resource_id'], 99999)

    def test_validation_error_structure(self):
        """Test estructura de respuesta para errores de validación."""
        invalid_fields = {
            'status': 'Estado inválido',
            'amount': 'Debe ser mayor a 0'
        }

        response = PermissionDenied.validation_error(
            "Datos inválidos",
            invalid_fields
        )

        self.assertFalse(response['success'])
        data = response['data']
        self.assertEqual(data['error_type'], 'validation_error')
        self.assertIn('invalid_fields', data)
        self.assertIn('details', data)
        self.assertEqual(data['details'], invalid_fields)

    def test_different_actions_have_appropriate_messages(self):
        """Test que diferentes acciones generan mensajes apropiados."""
        actions = ['access', 'modify', 'delete', 'view']

        for action in actions:
            response = PermissionDenied.purchase_access_denied(1, 123, action)
            message = response['message']

            # Verificar que el mensaje contiene la acción apropiada
            if action == 'access':
                self.assertIn('acceder a', message)
            elif action == 'modify':
                self.assertIn('modificar', message)
            elif action == 'delete':
                self.assertIn('eliminar', message)
            elif action == 'view':
                self.assertIn('ver', message)

    def test_admin_required_messages(self):
        """Test que mensajes de admin requerido sean apropiados."""
        actions = ['delete_purchase', 'cancel_paid',
                   'reactivate_cancelled', 'access_analytics']

        for action in actions:
            response = PermissionDenied.admin_required(action)
            message = response['message']

            # Verificar que el mensaje es informativo
            self.assertIn('administrador', message.lower())
            self.assertTrue(len(message) > 10,
                            f"Mensaje muy corto para acción {action}")


if __name__ == '__main__':
    print("Ejecutando tests básicos de PermissionDenied...")
    unittest.main(verbosity=2)
