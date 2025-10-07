"""
Mixins para vistas que centralizan decoradores y funcionalidad común.

Este módulo contiene mixins reutilizables para eliminar código duplicado
en las vistas, especialmente en documentación Swagger y patrones CRUD.
"""

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import status
from api.view_tags import notification_templates_admin


class SwaggerCRUDMixin:
    """
    Mixin que proporciona documentación Swagger estandarizada para operaciones CRUD.

    Attributes:
        swagger_tags (list): Tags para agrupar endpoints en Swagger
        model_name (str): Nombre del modelo para personalizar mensajes  
        serializer_class: Clase del serializer para request/response body
    """

    swagger_tags = ['API']
    model_name = 'Recurso'

    def get_swagger_tags(self):
        """Obtiene los tags de Swagger para este ViewSet."""
        return getattr(self, 'swagger_tags', ['API'])

    def get_model_name(self):
        """Obtiene el nombre del modelo para personalizar mensajes."""
        return getattr(self, 'model_name', 'Recurso')

    def get_serializer_class_for_swagger(self):
        """Obtiene la clase del serializer para documentación."""
        return getattr(self, 'serializer_class', None)

    @swagger_auto_schema(
        operation_summary="Listar recursos",
        operation_description="Obtiene una lista paginada de todos los recursos disponibles",
        responses={
            200: "Lista de recursos obtenida exitosamente",
            403: openapi.Response(description="Sin permisos de acceso"),
        }
    )
    def list(self, request, *args, **kwargs):
        """Documentación automática para listar recursos."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Obtener recurso",
        operation_description="Obtiene los detalles de un recurso específico por su ID",
        responses={
            200: "Recurso obtenido exitosamente",
            404: openapi.Response(description="Recurso no encontrado"),
            403: openapi.Response(description="Sin permisos de acceso"),
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Documentación automática para obtener un recurso."""
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Crear recurso",
        operation_description="Crea un nuevo recurso en el sistema",
        responses={
            201: "Recurso creado exitosamente",
            400: openapi.Response(description="Datos inválidos"),
            403: openapi.Response(description="Sin permisos de acceso"),
        }
    )
    def create(self, request, *args, **kwargs):
        """Documentación automática para crear un recurso."""
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Actualizar recurso completo",
        operation_description="Actualiza todos los campos de un recurso existente",
        responses={
            200: "Recurso actualizado exitosamente",
            400: openapi.Response(description="Datos inválidos"),
            404: openapi.Response(description="Recurso no encontrado"),
            403: openapi.Response(description="Sin permisos de acceso"),
        }
    )
    def update(self, request, *args, **kwargs):
        """Documentación automática para actualizar un recurso."""
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Actualizar recurso parcial",
        operation_description="Actualiza campos específicos de un recurso existente",
        responses={
            200: "Recurso actualizado exitosamente",
            400: openapi.Response(description="Datos inválidos"),
            404: openapi.Response(description="Recurso no encontrado"),
            403: openapi.Response(description="Sin permisos de acceso"),
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """Documentación automática para actualizar parcialmente un recurso."""
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Eliminar recurso",
        operation_description="Elimina un recurso del sistema de forma permanente",
        responses={
            204: openapi.Response(description="Recurso eliminado exitosamente"),
            404: openapi.Response(description="Recurso no encontrado"),
            403: openapi.Response(description="Sin permisos de acceso"),
        }
    )
    def destroy(self, request, *args, **kwargs):
        """Documentación automática para eliminar un recurso."""
        return super().destroy(request, *args, **kwargs)


class NotificationTemplateSwaggerMixin(SwaggerCRUDMixin):
    """
    Mixin específico para NotificationTemplate con documentación personalizada.
    """

    swagger_tags = notification_templates_admin()
    model_name = 'Plantilla de Notificación'

    @swagger_auto_schema(
        operation_summary="Listar plantillas de notificación",
        operation_description="Obtiene una lista de todas las plantillas de notificación del sistema",
        responses={
            200: "Lista de plantillas obtenida exitosamente",
            403: openapi.Response(description="Sin permisos de administrador"),
        },
        tags=notification_templates_admin()
    )
    def list(self, request, *args, **kwargs):
        return super(SwaggerCRUDMixin, self).list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Obtener plantilla de notificación",
        operation_description="Obtiene los detalles de una plantilla de notificación específica",
        responses={
            200: "Plantilla obtenida exitosamente",
            404: openapi.Response(description="Plantilla no encontrada"),
            403: openapi.Response(description="Sin permisos de administrador"),
        },
        tags=notification_templates_admin()
    )
    def retrieve(self, request, *args, **kwargs):
        return super(SwaggerCRUDMixin, self).retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Crear plantilla de notificación",
        operation_description="Crea una nueva plantilla de notificación en el sistema",
        responses={
            201: "Plantilla creada exitosamente",
            400: openapi.Response(description="Datos inválidos"),
            403: openapi.Response(description="Sin permisos de administrador"),
        },
        tags=notification_templates_admin()
    )
    def create(self, request, *args, **kwargs):
        return super(SwaggerCRUDMixin, self).create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Actualizar plantilla completa",
        operation_description="Actualiza todos los campos de una plantilla de notificación",
        responses={
            200: "Plantilla actualizada exitosamente",
            400: openapi.Response(description="Datos inválidos"),
            404: openapi.Response(description="Plantilla no encontrada"),
            403: openapi.Response(description="Sin permisos de administrador"),
        },
        tags=notification_templates_admin()
    )
    def update(self, request, *args, **kwargs):
        return super(SwaggerCRUDMixin, self).update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Actualizar plantilla parcial",
        operation_description="Actualiza campos específicos de una plantilla de notificación",
        responses={
            200: "Plantilla actualizada exitosamente",
            400: openapi.Response(description="Datos inválidos"),
            404: openapi.Response(description="Plantilla no encontrada"),
            403: openapi.Response(description="Sin permisos de administrador"),
        },
        tags=notification_templates_admin()
    )
    def partial_update(self, request, *args, **kwargs):
        return super(SwaggerCRUDMixin, self).partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Eliminar plantilla",
        operation_description="Elimina una plantilla de notificación del sistema",
        responses={
            204: openapi.Response(description="Plantilla eliminada exitosamente"),
            404: openapi.Response(description="Plantilla no encontrada"),
            403: openapi.Response(description="Sin permisos de administrador"),
        },
        tags=notification_templates_admin()
    )
    def destroy(self, request, *args, **kwargs):
        return super(SwaggerCRUDMixin, self).destroy(request, *args, **kwargs)


class UserSwaggerMixin(SwaggerCRUDMixin):
    """
    Mixin específico para User con documentación personalizada.

    Centraliza todos los decoradores Swagger para eliminar redundancia
    en UserViewSet, incluyendo casos especiales como el registro público
    y las restricciones de eliminación.

    Elimina aproximadamente 100 líneas de código duplicado al consolidar
    todos los decoradores @swagger_auto_schema y @extend_schema repetitivos.
    """

    swagger_tags = ['Users']
    model_name = 'Usuario'

    @swagger_auto_schema(
        operation_summary="Listar usuarios",
        operation_description="Lista usuarios del sistema. Los superusuarios ven todos, usuarios normales solo ven su propio perfil",
        responses={
            200: "Lista de usuarios obtenida exitosamente",
            401: openapi.Response(description="No autenticado")
        },
        tags=['Users']
    )
    def list(self, request, *args, **kwargs):
        return super(SwaggerCRUDMixin, self).list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Obtener usuario específico",
        operation_description="Obtiene detalles de un usuario. Solo superusuarios pueden ver otros usuarios",
        responses={
            200: "Usuario encontrado exitosamente",
            401: openapi.Response(description="No autenticado"),
            404: openapi.Response(description="Usuario no encontrado")
        },
        tags=['Users']
    )
    def retrieve(self, request, *args, **kwargs):
        return super(SwaggerCRUDMixin, self).retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Registrar nuevo usuario",
        operation_description="Crea una nueva cuenta de usuario en el sistema",
        responses={
            201: "Usuario creado exitosamente",
            400: openapi.Response(description="Datos inválidos")
        },
        tags=['Users']
    )
    def create(self, request, *args, **kwargs):
        return super(SwaggerCRUDMixin, self).create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Actualizar usuario completo",
        operation_description="Actualiza todos los campos de un usuario",
        responses={
            200: "Usuario actualizado exitosamente",
            400: openapi.Response(description="Datos inválidos"),
            401: openapi.Response(description="No autenticado"),
            404: openapi.Response(description="Usuario no encontrado")
        },
        tags=['Users']
    )
    def update(self, request, *args, **kwargs):
        return super(SwaggerCRUDMixin, self).update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Actualizar usuario parcial",
        operation_description="Actualiza campos específicos de un usuario",
        responses={
            200: "Usuario actualizado exitosamente",
            400: openapi.Response(description="Datos inválidos"),
            401: openapi.Response(description="No autenticado"),
            404: openapi.Response(description="Usuario no encontrado")
        },
        tags=['Users']
    )
    def partial_update(self, request, *args, **kwargs):
        return super(SwaggerCRUDMixin, self).partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Eliminar usuario",
        operation_description="Elimina un usuario del sistema. Solo superusuarios pueden eliminar usuarios y no pueden eliminar su propia cuenta",
        responses={
            200: openapi.Response(
                description="Usuario eliminado exitosamente",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            403: openapi.Response(
                description="Sin permisos o intento de auto-eliminación",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            500: openapi.Response(
                description="Error interno del servidor",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        },
        tags=['Users']
    )
    def destroy(self, request, *args, **kwargs):
        return super(SwaggerCRUDMixin, self).destroy(request, *args, **kwargs)
