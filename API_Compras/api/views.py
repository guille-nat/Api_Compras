from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from .models import NotificationTemplate
from .serializers import NotificationTemplateSerializer
from .view_mixins import NotificationTemplateSwaggerMixin

# Note: drf_yasg imports removed as they're now handled in the mixin


class NotificationTemplateViewSet(NotificationTemplateSwaggerMixin, viewsets.ModelViewSet):
    """
    ViewSet para gestionar plantillas de notificaciones del sistema.

    Proporciona operaciones CRUD completas para las plantillas de notificaciones
    que son utilizadas para enviar mensajes automáticos a los usuarios.
    Solo los administradores pueden gestionar estas plantillas.

    La documentación Swagger se maneja automáticamente a través del mixin
    NotificationTemplateSwaggerMixin para evitar código duplicado.
    """

    queryset = NotificationTemplate.objects.all()
    permission_classes = [IsAdminUser]
    serializer_class = NotificationTemplateSerializer

    # Todos los métodos CRUD (list, retrieve, create, update, partial_update, destroy)
    # están documentados automáticamente por el mixin NotificationTemplateSwaggerMixin
    # Esto elimina ~80 líneas de código repetitivo de decoradores @swagger_auto_schema
