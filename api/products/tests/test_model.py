from django.test import TestCase
from ..models import Product


class ProductModelTest(TestCase):
    def setUp(self):
        """Crea un producto de prueba en la base de datos."""
        self.product = Product.objects.create(
            product_code="PLA-NIK-AZU-S",
            name="razer viper",
            brand="razer",
            model="razer viper ultimate",
            unit_price="300",
            stock=20
        )

    def test_product_creation(self):
        """Test para verificar la creación fue correcta."""
        self.assertEqual(self.product.name, "razer viper")
        self.assertEqual(self.product.unit_price, "300")
        self.assertEqual(self.product.stock, 20)

    def test_produt_str(self):
        """Prueba el método __str__ del modelo"""
        self.assertEqual(str(self.product),
                         "razer viper (razer - razer viper ultimate)")
