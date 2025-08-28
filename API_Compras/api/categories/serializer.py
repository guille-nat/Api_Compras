# serializers.py
from rest_framework import serializers
from .models import Category


class CategoryPrivateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id", "name",
            "created_by", "created_at", "updated_by", "updated_at",
        ]
        read_only_fields = ["id", "created_by",
                            "created_at", "updated_by", "updated_at"]

    def validate_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("El nombre es demasiado corto.")
        return value.strip()


class CategoryPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]
