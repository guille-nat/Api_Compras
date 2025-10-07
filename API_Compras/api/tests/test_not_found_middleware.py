"""
Tests para el middleware de manejo de errores 404.

Verifica que el middleware intercepte correctamente las respuestas 404
y devuelva respuestas JSON estructuradas según los estándares del proyecto.
"""

import json
import pytest
from django.test import TestCase, RequestFactory, override_settings
from django.http import Http404, HttpResponse
from django.contrib.auth import get_user_model
from api.middleware.not_found_middleware import NotFoundErrorMiddleware

User = get_user_model()


class NotFoundErrorMiddlewareTest(TestCase):
    """
    Tests para el middleware NotFoundErrorMiddleware.
    """

    def setUp(self):
        """
        Configuración inicial para los tests.
        """
        self.factory = RequestFactory()
        self.middleware = NotFoundErrorMiddleware(
            get_response=self._dummy_get_response)

        # Crear usuario de prueba
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def _dummy_get_response(self, request):
        """
        Función dummy que simula una respuesta 404.
        """
        return HttpResponse(status=404)

    def test_is_api_request_with_api_path(self):
        """
        Test que verifica que se identifiquen correctamente las rutas de API.
        """
        request = self.factory.get('/api/v2/purchases/nonexistent/')

        result = self.middleware._is_api_request(request)

        self.assertTrue(result)

    def test_is_api_request_with_json_accept_header(self):
        """
        Test que verifica la identificación por header Accept.
        """
        request = self.factory.get(
            '/some/path/', HTTP_ACCEPT='application/json')

        result = self.middleware._is_api_request(request)

        self.assertTrue(result)

    def test_is_api_request_with_json_content_type(self):
        """
        Test que verifica la identificación por Content-Type.
        """
        request = self.factory.post('/some/path/',
                                    content_type='application/json',
                                    data='{}')

        result = self.middleware._is_api_request(request)

        self.assertTrue(result)

    def test_is_not_api_request(self):
        """
        Test que verifica que no se identifiquen rutas no-API como API.
        """
        request = self.factory.get('/admin/some/path/')

        result = self.middleware._is_api_request(request)

        self.assertFalse(result)

    def test_process_response_404_api_request(self):
        """
        Test que verifica el procesamiento de respuestas 404 para rutas API.
        """
        request = self.factory.get('/api/v2/purchases/999999/')
        request.user = self.user

        # Simular respuesta 404
        response = HttpResponse(status=404)

        result = self.middleware.process_response(request, response)

        self.assertEqual(result.status_code, 404)
        self.assertEqual(result['Content-Type'], 'application/json')

        # Verificar estructura de la respuesta
        response_data = json.loads(result.content)
        self.assertFalse(response_data['success'])
        self.assertIn('compras', response_data['message'])
        self.assertEqual(response_data['data']
                         ['error_type'], 'endpoint_not_found')
        self.assertEqual(
            response_data['data']['requested_path'], '/api/v2/purchases/999999/')
        self.assertEqual(response_data['data']['method'], 'GET')

    def test_process_response_404_non_api_request(self):
        """
        Test que verifica que no se procesen respuestas 404 de rutas no-API.
        """
        request = self.factory.get('/admin/some/path/')
        request.user = self.user

        # Simular respuesta 404
        original_response = HttpResponse(status=404)

        result = self.middleware.process_response(request, original_response)

        # Debe devolver la respuesta original sin modificar
        self.assertEqual(result, original_response)

    def test_process_response_non_404(self):
        """
        Test que verifica que no se procesen respuestas que no sean 404.
        """
        request = self.factory.get('/api/v2/purchases/')
        request.user = self.user

        # Simular respuesta 200
        original_response = HttpResponse(status=200)

        result = self.middleware.process_response(request, original_response)

        # Debe devolver la respuesta original sin modificar
        self.assertEqual(result, original_response)

    def test_create_404_response_purchases(self):
        """
        Test específico para endpoints de compras.
        """
        request = self.factory.get('/api/v2/purchases/invalid/')
        request.user = self.user

        response = self.middleware._create_404_response(request)
        response_data = json.loads(response.content)

        self.assertIn('compras', response_data['message'])
        self.assertEqual(response_data['data']
                         ['error_type'], 'endpoint_not_found')
        self.assertIn('purchases', response_data['data']['suggestions'][0])

    def test_create_404_response_products(self):
        """
        Test específico para endpoints de productos.
        """
        request = self.factory.get('/api/v2/products/invalid/')
        request.user = self.user

        response = self.middleware._create_404_response(request)
        response_data = json.loads(response.content)

        self.assertIn('productos', response_data['message'])
        self.assertEqual(response_data['data']
                         ['error_type'], 'endpoint_not_found')
        self.assertIn('products', response_data['data']['suggestions'][0])

    def test_create_404_response_users(self):
        """
        Test específico para endpoints de usuarios.
        """
        request = self.factory.get('/api/v2/users/invalid/')
        request.user = self.user

        response = self.middleware._create_404_response(request)
        response_data = json.loads(response.content)

        self.assertIn('usuarios', response_data['message'])
        self.assertEqual(response_data['data']
                         ['error_type'], 'endpoint_not_found')
        self.assertIn('users', response_data['data']['suggestions'][0])

    def test_create_404_response_payments(self):
        """
        Test específico para endpoints de pagos.
        """
        request = self.factory.get('/api/v2/payments/invalid/')
        request.user = self.user

        response = self.middleware._create_404_response(request)
        response_data = json.loads(response.content)

        self.assertIn('pagos', response_data['message'])
        self.assertEqual(response_data['data']
                         ['error_type'], 'endpoint_not_found')
        self.assertIn('payments', response_data['data']['suggestions'][0])

    def test_create_404_response_generic_api(self):
        """
        Test para endpoints genéricos de API.
        """
        request = self.factory.get('/api/v2/invalid/')
        request.user = self.user

        response = self.middleware._create_404_response(request)
        response_data = json.loads(response.content)

        self.assertIn('API', response_data['message'])
        self.assertEqual(response_data['data']
                         ['error_type'], 'endpoint_not_found')
        self.assertIn('purchases', response_data['data']['suggestions'][0])

    def test_get_endpoint_suggestions_v1_deprecation(self):
        """
        Test que verifica las sugerencias para versiones obsoletas.
        """
        suggestions = self.middleware._get_endpoint_suggestions(
            '/api/v1/purchases/')

        self.assertIn('v2', suggestions[0])
        self.assertIn('v1', suggestions[0])

    def test_get_endpoint_suggestions_purchase_context(self):
        """
        Test que verifica las sugerencias específicas para compras.
        """
        suggestions = self.middleware._get_endpoint_suggestions(
            '/api/v2/purchase/invalid/')

        purchase_suggestions = [s for s in suggestions if 'purchases' in s]
        self.assertTrue(len(purchase_suggestions) > 0)

    def test_get_endpoint_suggestions_limit(self):
        """
        Test que verifica que las sugerencias estén limitadas a 3.
        """
        suggestions = self.middleware._get_endpoint_suggestions(
            '/api/v2/purchase/invalid/')

        self.assertLessEqual(len(suggestions), 3)

    def test_middleware_logging(self):
        """
        Test que verifica que se haga logging de los errores 404.
        """
        import logging
        from unittest.mock import patch

        # Usar un mock para capturar las llamadas al logger
        with patch('api.middleware.not_found_middleware.logger') as mock_logger:
            request = self.factory.get('/api/v2/purchases/999999/')
            request.user = self.user

            response = HttpResponse(status=404)
            result = self.middleware.process_response(request, response)

            # Verificar que se llamó al logger.info
            mock_logger.info.assert_called_once()

            # Obtener el mensaje que se pasó al logger
            call_args = mock_logger.info.call_args[0][0]

            # Verificar el contenido del mensaje
            self.assertIn('404 error for API endpoint', call_args)
            self.assertIn('GET', call_args)
            self.assertIn('/api/v2/purchases/999999/', call_args)
            self.assertIn('testuser', call_args)

            # Verificar que se devolvió una respuesta JSON 404
            self.assertEqual(result.status_code, 404)

    def test_middleware_logging_integration(self):
        """
        Test de integración que verifica el logging funcionalmente sin atrapar logs.
        """
        # Este test simplemente verifica que el middleware puede ejecutarse
        # con logging sin causar errores, sin intentar capturar los logs
        request = self.factory.get('/api/v2/products/999999/')
        request.user = self.user

        response = HttpResponse(status=404)

        # El middleware debería procesar sin errores y devolver una respuesta JSON
        result = self.middleware.process_response(request, response)

        # Verificar que devuelve la respuesta correcta
        self.assertEqual(result.status_code, 404)
        self.assertEqual(result['Content-Type'], 'application/json')

        response_data = json.loads(result.content)
        self.assertFalse(response_data['success'])
        self.assertIn('productos', response_data['message'])

    def test_middleware_full_flow(self):
        """
        Test que verifica el flujo completo del middleware usando __call__.
        """
        request = self.factory.get('/api/v2/nonexistent/endpoint/')
        request.user = self.user

        # Usar el middleware completo que debería llamar a _dummy_get_response
        result = self.middleware(request)

        # Debería devolver una respuesta JSON 404
        self.assertEqual(result.status_code, 404)
        if hasattr(result, 'content'):
            response_data = json.loads(result.content)
            self.assertFalse(response_data['success'])

    def test_dummy_get_response_coverage(self):
        """
        Test para cubrir la función _dummy_get_response.
        """
        request = self.factory.get('/api/v2/test/')

        # Llamar directamente a la función dummy
        response = self._dummy_get_response(request)

        self.assertEqual(response.status_code, 404)

    def test_logging_without_exception(self):
        """
        Test que verifica que el logging no causa excepciones.
        """
        request = self.factory.get('/api/v2/purchases/invalid/')
        request.user = self.user

        response = HttpResponse(status=404)

        # Este test simplemente verifica que no se lance una excepción
        # cuando se procesa una respuesta 404
        try:
            result = self.middleware.process_response(request, response)
            self.assertEqual(result.status_code, 404)
        except Exception as e:
            self.fail(f"El middleware de logging causó una excepción: {e}")

    def test_user_without_username_attribute(self):
        """
        Test que cubre el caso donde el usuario tiene is_anonymous pero no username.
        """
        from unittest.mock import Mock

        request = self.factory.get('/api/v2/purchases/invalid/')

        # Crear un mock user que tenga is_anonymous pero no username
        mock_user = Mock()
        mock_user.is_anonymous = False

        # Eliminar el atributo username del mock para simular el caso específico
        try:
            del mock_user.username
        except AttributeError:
            pass  # Ya no tiene username

        # Verificar que efectivamente no tiene username
        self.assertFalse(hasattr(mock_user, 'username'))

        request.user = mock_user

        response = HttpResponse(status=404)
        result = self.middleware.process_response(request, response)

        self.assertEqual(result.status_code, 404)
        response_data = json.loads(result.content)
        self.assertFalse(response_data['success'])

    def test_anonymous_user_handling(self):
        """
        Test que verifica el manejo de usuarios anónimos.
        """
        from django.contrib.auth.models import AnonymousUser

        request = self.factory.get('/api/v2/purchases/invalid/')
        request.user = AnonymousUser()  # Asignar usuario anónimo explícitamente

        response = HttpResponse(status=404)
        result = self.middleware.process_response(request, response)

        self.assertEqual(result.status_code, 404)
        response_data = json.loads(result.content)
        self.assertFalse(response_data['success'])

    def test_no_user_attribute_handling(self):
        """
        Test que verifica el manejo cuando no existe el atributo user.
        """
        request = self.factory.get('/api/v2/purchases/invalid/')
        # No asignar request.user para simular el caso donde no existe

        response = HttpResponse(status=404)
        result = self.middleware.process_response(request, response)

        self.assertEqual(result.status_code, 404)
        response_data = json.loads(result.content)
        self.assertFalse(response_data['success'])

    def test_create_404_response_non_api_path(self):
        """
        Test para rutas que no son específicamente de API conocidas.
        """
        request = self.factory.get(
            '/some/unknown/path/', HTTP_ACCEPT='application/json')
        request.user = self.user

        response = self.middleware._create_404_response(request)
        response_data = json.loads(response.content)

        # Debe usar el mensaje genérico (else case)
        self.assertIn('El recurso solicitado no fue encontrado',
                      response_data['message'])
        self.assertEqual(response_data['data']
                         ['error_type'], 'endpoint_not_found')
        self.assertEqual(response_data['data']
                         ['requested_path'], '/some/unknown/path/')

    def test_response_structure_completeness(self):
        """
        Test que verifica que la respuesta tenga todos los campos requeridos.
        """
        request = self.factory.get('/api/v2/invalid/endpoint/')
        request.user = self.user

        response = self.middleware._create_404_response(request)
        response_data = json.loads(response.content)

        # Verificar estructura base
        self.assertIn('success', response_data)
        self.assertIn('message', response_data)
        self.assertIn('data', response_data)

        # Verificar datos específicos
        data = response_data['data']
        self.assertIn('error_type', data)
        self.assertIn('requested_path', data)
        self.assertIn('method', data)
        self.assertIn('available_versions', data)
        self.assertIn('documentation_url', data)
        self.assertIn('suggestions', data)

        # Verificar tipos
        self.assertIsInstance(response_data['success'], bool)
        self.assertIsInstance(response_data['message'], str)
        self.assertIsInstance(data['suggestions'], list)
        self.assertIsInstance(data['available_versions'], list)

    def test_create_404_response_categories(self):
        """
        Test específico para endpoints de categorías.
        """
        request = self.factory.get('/api/v2/categories/invalid/')
        request.user = self.user

        response = self.middleware._create_404_response(request)
        response_data = json.loads(response.content)

        self.assertIn('categorías', response_data['message'])
        self.assertEqual(response_data['data']
                         ['error_type'], 'endpoint_not_found')

    def test_create_404_response_inventories(self):
        """
        Test específico para endpoints de inventarios.
        """
        request = self.factory.get('/api/v2/inventories/invalid/')
        request.user = self.user

        response = self.middleware._create_404_response(request)
        response_data = json.loads(response.content)

        self.assertIn('inventarios', response_data['message'])
        self.assertEqual(response_data['data']
                         ['error_type'], 'endpoint_not_found')

    def test_create_404_response_analytics(self):
        """
        Test específico para endpoints de analíticas.
        """
        request = self.factory.get('/api/v2/analytics/invalid/')
        request.user = self.user

        response = self.middleware._create_404_response(request)
        response_data = json.loads(response.content)

        self.assertIn('analíticas', response_data['message'])
        self.assertEqual(response_data['data']
                         ['error_type'], 'endpoint_not_found')

    def test_create_404_response_promotions(self):
        """
        Test específico para endpoints de promociones.
        """
        request = self.factory.get('/api/v2/promotions/invalid/')
        request.user = self.user

        response = self.middleware._create_404_response(request)
        response_data = json.loads(response.content)

        self.assertIn('promociones', response_data['message'])
        self.assertEqual(response_data['data']
                         ['error_type'], 'endpoint_not_found')

    def test_create_404_response_storage_location(self):
        """
        Test específico para endpoints de ubicaciones de almacenamiento.
        """
        request = self.factory.get('/api/v2/storage-locations/invalid/')
        request.user = self.user

        response = self.middleware._create_404_response(request)
        response_data = json.loads(response.content)

        # Este caso debería caer en el genérico ya que no hay condición específica
        self.assertIn('API', response_data['message'])
        self.assertEqual(response_data['data']
                         ['error_type'], 'endpoint_not_found')
