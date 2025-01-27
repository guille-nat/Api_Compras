from rest_framework import serializers
from .models import Productos


class ProductsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Productos
        fields = [
            'id', 'cod_productos', 'nombre',
            'marca', 'modelo', 'precio_unitario',
            'stock'
        ]
        read_only_fields = ['id',]
