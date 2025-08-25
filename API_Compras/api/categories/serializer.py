from rest_framework.serializers import ModelSerializer
from .models import Category


class CategorySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
        read_only_fields = [
            'id',
            'created_by',
            'created_at',
            'updated_by',
            'updated_at'
        ]
