from django.contrib.auth.models import User
from rest_framework import serializers
from django.db import transaction
from django.utils import timezone


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
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
            # password = validated_data.pop('password')

            user = User.objects.create_user(
                username=validated_data['username'],
                email=validated_data.get('email'),
                password=validated_data['password'],
                first_name=validated_data.get('first_name', ''),
                last_name=validated_data.get('last_name', ''),
                last_login=timezone.now()
            )
            # user.set_password(password)

            # Crear el perfil asociado si los datos del perfil están presentes
            return user
