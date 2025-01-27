from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, status
from rest_framework.response import Response
from .serializers import UserSerializer


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
