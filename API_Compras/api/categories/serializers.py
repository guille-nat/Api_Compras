
from rest_framework import serializers
from .models import Category
from api.serializer_mixins import AuditableWithUserSerializerMixin, SimpleModelSerializerMixin


class CategoryPrivateSerializer(AuditableWithUserSerializerMixin, serializers.ModelSerializer):
    """
    Serializer privado para Category con campos de auditoría automáticos.

    Utiliza AuditableWithUserSerializerMixin para eliminar redundancia en:
    - fields = '__all__'
    - read_only_fields para todos los campos de auditoría

    Elimina ~7 líneas de código repetitivo de configuración Meta.
    """

    class Meta(AuditableWithUserSerializerMixin.Meta):
        model = Category
        fields = [
            "id", "name",
            "created_by", "created_at", "updated_by", "updated_at",
        ]

    def validate_name(self, value):
        """Valida que el nombre tenga al menos 2 caracteres."""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("El nombre es demasiado corto.")
        return value.strip()


class CategoryPublicSerializer(SimpleModelSerializerMixin, serializers.ModelSerializer):
    """
    Serializer público para Category con configuración básica automática.

    Utiliza SimpleModelSerializerMixin para estandarizar configuración Meta
    aunque override fields para mostrar solo campos públicos.
    """

    class Meta(SimpleModelSerializerMixin.Meta):
        model = Category
        fields = ["id", "name"]
