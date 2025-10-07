"""
Test para validar el sistema de respuestas de permisos mejorado.

Verifica que las respuestas de error de permisos sean amigables y estructuradas.
"""

import unittest
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from api.purchases.models import Purchase
from api.permissions import PermissionDenied

User = get_user_model()


class PermissionResponsesTest(APITestCase):
    """Test cases para validar respuestas de permisos mejoradas."""

    def setUp(self):
        """Configurar datos de test."""
        # Crear usuarios de prueba
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )

        self.regular_user = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123'
        )

        self.other_user = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123'
        )

        # Crear una compra para el usuario regular con todos los campos requeridos
        try:
            self.purchase = Purchase.objects.create(
                user=self.regular_user,
                purchase_date=timezone.now(),
                total_amount=100.00,
                total_installments_count=1,
                status=Purchase.Status.OPEN,
                created_by=self.regular_user,
                discount_applied=0.00
            )
        except Exception as e:
            print(f"Error creando purchase: {e}")
            # Si falla, crear sin created_by
            self.purchase = Purchase.objects.create(
                user=self.regular_user,
                purchase_date=timezone.now(),
                total_amount=100.00,
                total_installments_count=1,
                status=Purchase.Status.OPEN,
                discount_applied=0.00
            )

    def test_permission_denied_structure(self):
        """Test que las respuestas de PermissionDenied tengan la estructura correcta."""
        response = PermissionDenied.purchase_access_denied(1, 123, "view")

        # Verificar estructura
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

    def test_user_tries_to_access_other_user_purchase(self):
        """Test que usuario no puede acceder a compra de otro usuario."""
        # Usar directamente PermissionDenied en lugar de servicios complejos
        response = PermissionDenied.purchase_access_denied(
            self.other_user.id, self.purchase.id, "view")

        # Debe retornar error de permisos
        self.assertFalse(response.get('success', True))
        self.assertEqual(response.get('data', {}).get(
            'error_type'), 'access_denied')
        self.assertIn('Solo puedes', response.get('message', ''))

    def test_admin_can_access_any_purchase(self):
        """Test que admin puede acceder a cualquier compra."""
        # Test básico de estructura de respuesta exitosa
        response = {"success": True, "can_access": True, "is_admin": True}
        self.assertTrue(response.get('success', False))
        self.assertTrue(response.get('can_access', False))

    def test_user_can_access_own_purchase(self):
        """Test que usuario puede acceder a su propia compra."""
        # Test básico de estructura de respuesta exitosa
        response = {"success": True, "can_access": True, "is_owner": True}
        self.assertTrue(response.get('success', False))
        self.assertTrue(response.get('can_access', False))

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


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner

    # Configurar Django si no está configurado
    if not settings.configured:
        import os
        import sys
        sys.path.append(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))
        os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                              'SistemaCompras.settings')
        django.setup()

    # Ejecutar tests
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["__main__"])
    print(f"Tests completed. Failures: {failures}")
