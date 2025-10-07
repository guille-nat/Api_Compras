from rest_framework import serializers
from .models import NotificationTemplate
from .serializer_mixins import UserContextSerializerMixin, AuditableWithUserSerializerMixin


class NotificationTemplateSerializer(UserContextSerializerMixin, AuditableWithUserSerializerMixin, serializers.ModelSerializer):
    """
    Serializer para NotificationTemplate con auditoría automática.

    Utiliza mixins para eliminar código duplicado:
    - AuditableWithUserSerializerMixin: Campos de auditoría read-only automáticos
    - UserContextSerializerMixin: Asignación automática de created_by/updated_by

    Esto elimina ~15 líneas de código repetitivo (Meta + create + update).
    """

    class Meta(AuditableWithUserSerializerMixin.Meta):
        model = NotificationTemplate
