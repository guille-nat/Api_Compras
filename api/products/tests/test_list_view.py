from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from ..models import Product


class ProductAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(
            product_code="PLA-NIK-AZU-S",
            name="razer viper",
            brand="razer",
            model="razer viper ultimate",
            unit_price="300",
            stock=20
        )

    def test_list_product(self):
        """Verifica que la API lista los productos correctamente"""
        response = self.client.get("/api/products")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "razer viper")
