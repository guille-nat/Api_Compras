from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """
    Permiso personalizado para solo permitir acceso a usuarios con is_superuser=True.
    """

    def has_permission(self, request, view):
        # Verifica si el usuario está autenticado y si es un superusuario
        return request.user and request.user.is_authenticated and request.user.is_superuser
