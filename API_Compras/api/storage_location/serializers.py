from rest_framework import serializers
from .models import StorageLocation as Location
from api.serializer_mixins import UserContextSerializerMixin, AuditableWithUserSerializerMixin


class LocationSerializer(UserContextSerializerMixin, AuditableWithUserSerializerMixin, serializers.ModelSerializer):
    """
    Serializer para StorageLocation con auditoría automática.

    Utiliza mixins para eliminar código duplicado:
    - AuditableWithUserSerializerMixin: Campos de auditoría read-only automáticos
    - UserContextSerializerMixin: Asignación automática de created_by/updated_by

    Esto elimina ~20 líneas de código repetitivo (Meta + create + update con validaciones).
    """

    class Meta(AuditableWithUserSerializerMixin.Meta):
        model = Location
