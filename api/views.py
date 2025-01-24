from django.shortcuts import render
from django.contrib.auth.models import User
from .serializers import (
    UserSerializer, ProductsSerializer,
    ComprasSerializer, NotificacionSerializer,

)
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework import generics
from .models import (
    Products, Compras,
    Pagos, Cuotas, DetallesCompras,
    Notificacion
)
from django.db import transaction
from .permissions import IsAdminUser


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # Permitir creación de usuarios sin autenticación
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.action == 'create':  # Permitir creación sin autenticación
            return [AllowAny()]
        return [IsAuthenticated()]  # Requerir autenticación para todo lo demás

    def get_queryset(self):
        if self.request.user.is_superuser:  # Mostrar todos los usuarios si es superusuario
            return User.objects.all()
        # Mostrar solo el usuario autenticado
        return User.objects.filter(id=self.request.user.id)

    def create(self, request, *args, **kwargs):
        """
        Crea un nuevo usuario sin necesidad de autenticación.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Usar una transacción para garantizar que el usuario y el perfil se creen juntos
        with transaction.atomic():
            password = serializer.validated_data.pop('password')
            user = User(**serializer.validated_data)
            user.set_password(password)
            user.save()

        return Response(self.get_serializer(user).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()

            # Evitar eliminación de la propia cuenta
            if instance == request.user:
                return Response(
                    {'error': 'No puedes eliminar tu propia cuenta.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Solo superusuarios pueden eliminar usuarios
            if not request.user.is_superuser:
                return Response(
                    {'error': 'No estás autorizado para eliminar usuarios.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            username = instance.username
            instance.delete()
            return Response(
                {'error': f'Usuario {username} fue eliminado con éxito.'},
                status=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            # Captura cualquier excepción y devuelve un error 500
            return Response(
                {'error': f'Error interno del servidor: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductsViewSet(viewsets.ModelViewSet):
    queryset = Products.objects.all()
    serializer_class = ProductsSerializer

    def get_permissions(self):
        # Permitir acceso sin autenticación para las acciones 'list' y 'retrieve'
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        # Requerir autenticación para cualquier otra acción
        return [IsAdminUser()]


class CompraViewSet(viewsets.ModelViewSet):
    queryset = Compras.objects.all()
    serializer_class = ComprasSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Compras.objects.all()
        return Compras.objects.filter(usuario=self.request.user)


class NotificationListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificacionSerializer

    def get_queryset(self):
        return Notificacion.objects.filter(usuario=self.request.user)
