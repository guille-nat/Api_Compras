from api.users.models import CustomUser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, status
from rest_framework.response import Response
from .serializers import UserSerializer
from api.view_mixins import UserSwaggerMixin

# Note: drf_yasg and drf_spectacular imports removed as they're now handled in the mixin


class UserViewSet(UserSwaggerMixin, viewsets.ModelViewSet):
    """
    ViewSet para gestionar usuarios del sistema.

    Proporciona operaciones CRUD para usuarios con diferentes niveles de acceso.
    La creación es pública, pero otras operaciones requieren autenticación.

    La documentación Swagger se maneja automáticamente a través del mixin
    UserSwaggerMixin para evitar código duplicado (~100 líneas eliminadas).
    """

    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.action == 'create':  # Permitir creación sin autenticación
            return [AllowAny()]
        return [IsAuthenticated()]  # Requerir autenticación para todo lo demás

    def get_queryset(self):
        return CustomUser.objects.all().order_by("username") if self.request.user.is_superuser else CustomUser.objects.filter(id=self.request.user.id)

    def destroy(self, request, *args, **kwargs):
        """
        Elimina un usuario con validaciones específicas.

        Override del método destroy para implementar lógica de negocio específica:
        - Evitar auto-eliminación
        - Validar permisos de superusuario
        - Manejo de errores personalizado
        """
        # Resolve pk and perform permission checks explicitly to avoid queryset scoping surprises
        pk = kwargs.get('pk')
        if pk is None:
            return Response({'error': 'Falta identificador de usuario.'}, status=status.HTTP_400_BAD_REQUEST)

        # Try to fetch the target user directly
        from api.users.models import CustomUser as _CustomUser
        try:
            target = _CustomUser.objects.filter(pk=pk).first()
        except Exception:
            target = None

        if target is None:
            return Response({'error': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        # Evitar eliminación de la propia cuenta
        if target == request.user:
            return Response({'error': 'No puedes eliminar tu propia cuenta.'}, status=status.HTTP_403_FORBIDDEN)

        # Solo superusuarios pueden eliminar usuarios
        if not request.user.is_superuser:
            return Response({'error': 'No estás autorizado para eliminar usuarios.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            username = target.username
            target.delete()
            return Response({'message': f'Usuario {username} fue eliminado con éxito.'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': f'Error interno del servidor: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
