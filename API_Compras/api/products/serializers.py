from rest_framework import serializers
from .models import Product, ProductCategory
from api.categories.models import Category
from api.categories.serializers import CategoryPublicSerializer


class ProductCategorySerializer(serializers.ModelSerializer):
    """
    Serializer para la tabla intermedia ProductCategory.

    Incluye información adicional sobre la relación producto-categoría,
    como si es la categoría principal y detalles de asignación.
    """
    category = CategoryPublicSerializer(read_only=True)

    class Meta:
        model = ProductCategory
        fields = ['category', 'is_primary', 'assigned_at']
        read_only_fields = ['assigned_at']


class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer completo para productos con soporte de múltiples categorías.

    Incluye todas las categorías asociadas al producto a través de la
    tabla intermedia ProductCategory, mostrando información detallada
    de cada relación.
    """
    # Mostrar todas las categorías con información de relación
    productcategory_set = ProductCategorySerializer(many=True, read_only=True)

    # Campo calculado para obtener solo las categorías sin metadatos
    categories = CategoryPublicSerializer(many=True, read_only=True)

    # Campo calculado para la categoría principal
    primary_category = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'product_code', 'name', 'brand', 'model', 'unit_price',
            'categories', 'productcategory_set', 'primary_category',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_primary_category(self, obj):
        """
        Obtiene la categoría principal del producto.

        Returns:
            dict: Datos serializados de la categoría principal o None.
        """
        primary_category = obj.get_primary_category()
        if primary_category:
            return CategoryPublicSerializer(primary_category).data
        return None


class ProductBasicSerializer(serializers.ModelSerializer):
    """
    Serializer básico para productos que incluye solo información esencial.

    Utilizado en listados donde no se requiere información detallada
    de categorías para optimizar rendimiento.
    """
    primary_category = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'product_code', 'name', 'brand', 'model',
            'unit_price', 'primary_category'
        ]
        read_only_fields = ['id']

    def get_primary_category(self, obj):
        """
        Obtiene la categoría principal del producto.

        Returns:
            dict: Datos serializados de la categoría principal o None.
        """
        primary_category = obj.get_primary_category()
        if primary_category:
            return CategoryPublicSerializer(primary_category).data
        return None
