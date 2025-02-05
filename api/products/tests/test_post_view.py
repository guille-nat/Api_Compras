from django.test import TestCase
from api.users.models import CustomUser
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from ..models import Product


class ProductCreateAPITest(TestCase):
    def setUp(self):
        """Configurar cliente API y crear usuario con JWT"""
        self.client = APIClient()

        # Crear super usuario para poder hacer post en Products
        self.admin_user = CustomUser.objects.create_superuser(
            username='admin', password='adminpassword')

        # Obtener el token JWT
        response = self.client.post(
            '/api/token', {'username': 'admin', 'password': 'adminpassword'})
        self.token = response.data.get('access')

        # Agregar token a las solicitudes autenticadas
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_crate_product_as_superuser(self):
        """Verifica que un super usuario pueda crear un producto"""
        data = {
            "product_code": "PLA-NIK-AZU-M",
            "name": "logitech g pro x",
            "brand": "logitech",
            "model": "pro x superlight",
            "unit_price": 350.00,
            "stock": 15
        }
        response = self.client.post('/api/products', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_product_as_normal_user(self):
        """Verifica que un usuario normal NO pueda crear productos"""
        normal_user = CustomUser.objects.create_user(
            username='testuser', password='testpassword',
            first_name='testname', last_name='testlastname', email='test@email.com.ar',
            last_login=timezone.now()
        )

        # Obtener el token JWT
        response = self.client.post(
            '/api/token', {'username': 'testuser', 'password': 'testpassword'})
        token = response.data.get('access')

        # Cambiar credenciales a usuario normal
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        data = {
            "product_code": "PLA-NIK-AZU-M",
            "name": "logitech g pro x",
            "brand": "logitech",
            "model": "pro x superlight",
            "unit_price": 350.00,
            "stock": 15
        }

        response = self.client.post('/api/products', data, format='json')
        # No tiene permisos
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
