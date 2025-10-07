import re
from typing import List, Dict, Any, Union
from decimal import Decimal, InvalidOperation
from django.db import models
from .models import Product
from api.promotions.models import PromotionScopeProduct

# Patrones regex para validación de caracteres
VALID_PRODUCT_CODE_PATTERN = re.compile(r'^[A-Za-z0-9\s\-_]+$')
VALID_TEXT_PATTERN = re.compile(r'^[A-Za-z0-9\s\-_.,áéíóúÁÉÍÓÚñÑ]+$')

# Constantes de validación
MAX_TEXT_LENGTH = 120
MIN_TEXT_LENGTH = 1
MAX_PRICE_VALUE = Decimal('1000000000')
MIN_PRICE_VALUE = Decimal('0')


class ProductDataValidator:
    """
    Clase utilitaria para validación de datos de productos.

    Proporciona métodos estáticos reutilizables para validar diferentes
    campos de productos según las reglas de negocio establecidas.
    Utiliza patrones regex y validaciones de tipo para garantizar
    la integridad de los datos antes de operaciones de base de datos.
    """

    @staticmethod
    def product_code(code: str) -> bool:

        if not isinstance(code, str):
            return False

        if len(code) < MIN_TEXT_LENGTH or len(code) > MAX_TEXT_LENGTH:
            return False

        return VALID_PRODUCT_CODE_PATTERN.match(code) is not None

    @staticmethod
    def text_field(text: str) -> bool:

        if not isinstance(text, str):
            return False

        if len(text) < MIN_TEXT_LENGTH or len(text) > MAX_TEXT_LENGTH:
            return False

        return VALID_TEXT_PATTERN.match(text) is not None

    @staticmethod
    def price(price: Union[str, int, float, Decimal]) -> bool:

        try:
            decimal_price = Decimal(str(price))
        except (ValueError, TypeError, InvalidOperation):
            return False

        return MIN_PRICE_VALUE <= decimal_price < MAX_PRICE_VALUE

    @staticmethod
    def positive_integer(value: int) -> bool:
        return isinstance(value, int) and value > 0

    @staticmethod
    def required_fields(data: Dict[str, Any], fields: List[str]) -> bool:
        """
        Valida presencia de campos requeridos en diccionario.

        Parámetros:
            data (Dict[str, Any]): Diccionario con datos del producto
            fields (List[str]): Lista de campos requeridos

        Retorna:
            bool: True si todos los campos están presentes, False en caso contrario
        """
        if not isinstance(data, dict):
            return False

        for field in fields:
            if field not in data.keys() or data[field] is None:
                return False

        return True

    @staticmethod
    def single_product(product_data: Dict[str, Any]) -> bool:
        """
        Valida todos los campos de un producto individual aplicando
        todas las reglas de validación específicas.

        Parámetros:
            product_data (Dict[str, Any]): Diccionario con datos del producto

        Retorna:
            bool: True si el producto es completamente válido, False en caso contrario
        """
        required_fields = ["product_code", "name", "brand",
                           "model", "unit_price", "category_id", "user_id"]

        if not ProductDataValidator.required_fields(product_data, required_fields):
            return False

        if product_data.get("product_code"):
            if not ProductDataValidator.product_code(product_data["product_code"]):
                return False

        text_fields = ["name", "brand", "model"]
        for field_name in text_fields:
            field_value = product_data.get(field_name)
            if field_value and not ProductDataValidator.text_field(field_value):
                return False

        if not ProductDataValidator.price(product_data["unit_price"]):
            return False
        for id_field in ["category_id", "user_id"]:
            if not ProductDataValidator.positive_integer(product_data[id_field]):
                return False

        return True


def validate_product_data(data: List[Dict[str, Any]]) -> bool:
    """
    Valida lista de productos utilizando la clase ProductDataValidator.

    Utiliza la clase ProductDataValidator para aplicar validaciones
    individuales a cada producto de manera consistente y reutilizable.
    Implementa fail-fast para mejorar rendimiento.

    Parámetros:
        data (List[Dict[str, Any]]): Lista de diccionarios con datos de productos

    Retorna:
        bool: True si todos los productos son válidos, False en caso contrario
    """
    if not data or not isinstance(data, list):
        return False

    for product in data:
        if not ProductDataValidator.single_product(product):
            return False

    return True


def extract_product_codes(
    products: models.QuerySet[Product],
    promotions_scope: models.QuerySet[PromotionScopeProduct]
) -> list[dict[str, Any]]:
    """
    Asocia productos con sus promociones activas y reglas.

    Parámetros:
        products: QuerySet de productos.
        promotions_scope: QuerySet de promociones relacionadas.

    Retorna:
        Lista de diccionarios con datos del producto y sus promociones activas.
    """
    promotions_by_product = {}
    for promo_scope in promotions_scope:
        product_id = promo_scope.product.id
        if product_id not in promotions_by_product:
            promotions_by_product[product_id] = []
        promotions_by_product[product_id].append(promo_scope.promotion)

    products_with_promotions = []
    for product in products:
        product_promotions = promotions_by_product.get(product.id, [])

        active_promotions = []

        for promotion in product_promotions:
            promotion_data = {
                'id': promotion.id,
                'name': promotion.name,
                'active': promotion.active,
                'created_at': promotion.created_at,
                'updated_at': promotion.updated_at,
                'rules': []
            }
            if hasattr(promotion, 'active_rules') and promotion.active_rules:
                for rule in promotion.active_rules:
                    rule_data = {
                        'id': rule.id,
                        'type': rule.type,
                        'value': rule.value,
                        'priority': rule.priority,
                        'start_at': rule.start_at,
                        'end_at': rule.end_at,
                        'acumulable': rule.acumulable
                    }
                    promotion_data['rules'].append(rule_data)

            active_promotions.append(promotion_data)
        primary_category = product.get_primary_category()

        product_data = {
            'id': product.id,
            'product_code': product.product_code,
            'name': product.name,
            'brand': product.brand,
            'model': product.model,
            'unit_price': product.unit_price,

            'primary_category': {
                'id': primary_category.id,
                'name': primary_category.name
            } if primary_category else None,
            'categories': [
                {
                    'id': cat.id,
                    'name': cat.name,
                    'is_primary': cat.id == (primary_category.id if primary_category else None)
                }
                for cat in product.categories.all()
            ]
        }
        products_with_promotions.append({
            'product': product_data,
            'active_promotions': active_promotions
        })
    return products_with_promotions
