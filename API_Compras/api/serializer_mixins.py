"""
Mixins para serializers que centralizan patrones comunes y eliminan redundancia.

Este módulo contiene mixins reutilizables para eliminar código duplicado
en los serializers, especialmente en configuraciones Meta y métodos
create/update que siguen patrones similares.

Siguiendo el principio DRY (Don't Repeat Yourself), estos mixins permiten
centralizar la lógica común que se repite en múltiples serializers del proyecto.
"""

from rest_framework import serializers


class BaseModelSerializerMixin:
    """
    Mixin base para serializers que proporciona configuración Meta común.

    Centraliza patrones repetitivos como:
    - fields = '__all__'
    - read_only_fields básicos con 'id'

    Uso:
        class MySerializer(BaseModelSerializerMixin, serializers.ModelSerializer):
            class Meta(BaseModelSerializerMixin.Meta):
                model = MyModel
                # read_only_fields se hereda automáticamente
    """

    class Meta:
        fields = '__all__'
        read_only_fields = ('id',)


class AuditableSerializerMixin:
    """
    Mixin para serializers de modelos que tienen campos de auditoría.

    Centraliza el patrón repetitivo de campos de solo lectura para auditoría:
    - id, created_at, updated_at
    - created_by, updated_by (si existen)

    Uso:
        class MyAuditableSerializer(AuditableSerializerMixin, serializers.ModelSerializer):
            class Meta(AuditableSerializerMixin.Meta):
                model = MyAuditableModel
                # read_only_fields incluye automáticamente campos de auditoría
    """

    class Meta:
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class AuditableWithUserSerializerMixin:
    """
    Mixin para serializers de modelos con auditoría completa incluyendo usuarios.

    Extiende AuditableSerializerMixin para incluir también:
    - created_by, updated_by como campos de solo lectura

    Uso:
        class MyFullAuditSerializer(AuditableWithUserSerializerMixin, serializers.ModelSerializer):
            class Meta(AuditableWithUserSerializerMixin.Meta):
                model = MyFullAuditModel
    """

    class Meta:
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at',
                            'created_by', 'updated_by')


class UserContextSerializerMixin:
    """
    Mixin para serializers que necesitan asignar el usuario del request.

    Proporciona métodos create y update que automáticamente asignan
    el usuario actual a los campos created_by y updated_by.

    Requisitos:
    - El modelo debe tener campos 'created_by' y/o 'updated_by'
    - El serializer debe recibir el request en el contexto

    Uso:
        class MyUserAwareSerializer(UserContextSerializerMixin, AuditableWithUserSerializerMixin, serializers.ModelSerializer):
            class Meta(AuditableWithUserSerializerMixin.Meta):
                model = MyModelWithUser
    """

    def create(self, validated_data):
        """
        Crea una instancia asignando automáticamente created_by.

        Args:
            validated_data (dict): Datos validados para crear la instancia

        Returns:
            Model instance: La instancia creada con created_by asignado

        Raises:
            AttributeError: Si no hay request en el contexto
        """
        user = self.context.get(
            'request').user if self.context.get('request') else None
        if user and hasattr(self.Meta.model, 'created_by'):
            validated_data['created_by'] = user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Actualiza una instancia asignando automáticamente updated_by.

        Args:
            instance: La instancia a actualizar
            validated_data (dict): Datos validados para la actualización

        Returns:
            Model instance: La instancia actualizada con updated_by asignado

        Raises:
            AttributeError: Si no hay request en el contexto
        """
        user = self.context.get(
            'request').user if self.context.get('request') else None
        if user and hasattr(instance, 'updated_by'):
            validated_data['updated_by'] = user
        return super().update(instance, validated_data)


class SimpleModelSerializerMixin:
    """
    Mixin para serializers básicos que solo necesitan configuración mínima.

    Ideal para serializers simples que no requieren campos de auditoría
    pero sí necesitan read_only_fields básicos.

    Uso:
        class MySimpleSerializer(SimpleModelSerializerMixin, serializers.ModelSerializer):
            class Meta(SimpleModelSerializerMixin.Meta):
                model = MySimpleModel
                fields = ['id', 'name', 'description']  # Override si no quieres '__all__'
    """

    class Meta:
        fields = '__all__'
        read_only_fields = ('id',)
