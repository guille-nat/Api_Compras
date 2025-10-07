from .models import CustomUser
from rest_framework import serializers
from django.db import transaction


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email',
            'password', 'first_name', 'last_name'
        ]
        read_only_fields = ["id",]
        extra_kwargs = {
            'password': {'write_only': True},
            'last_login': {'write_only': True}
        }

    def create(self, validated_data):
        # Crear el usuario
        with transaction.atomic():
            # Extraer la contraseña y pasarla correctamente a create_user
            password = validated_data.pop('password')

            user = CustomUser.objects.create_user(
                username=validated_data.get('username'),
                email=validated_data.get('email'),
                password=password,
                first_name=validated_data.get('first_name', ''),
                last_name=validated_data.get('last_name', '')
            )

            # create_user ya guarda la contraseña hasheada; simplemente devolver la instancia
            return user
