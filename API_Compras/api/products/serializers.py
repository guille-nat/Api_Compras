from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 'product_code', 'name',
            'brand', 'model', 'unit_price',
            'stock'
        ]
        read_only_fields = ['id',]
