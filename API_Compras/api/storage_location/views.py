from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from api.view_tags import storage_admin
from .models import StorageLocation as Location
from .serializers import LocationSerializer
from api.cache import cache_manager, CacheKeys, CacheTimeouts
from api.view_mixins import SwaggerCRUDMixin
import logging

logger = logging.getLogger(__name__)


def _invalidate_storage_cache():
    """
    Invalida el cache relacionado con ubicaciones de almacenamiento.

    Esta función se ejecuta después de crear, actualizar o eliminar ubicaciones
    para asegurar que los datos en cache estén actualizados.
    """
    # Invalidar cache de ubicaciones de almacenamiento
    cache_manager.delete_pattern(f"{CacheKeys.STORAGE_LOCATIONS_LIST}*")
    cache_manager.delete_pattern(f"{CacheKeys.STORAGE_LOCATION_DETAIL}*")

    # También invalidar cache de inventario ya que las ubicaciones pueden afectar
    cache_manager.delete_pattern(f"{CacheKeys.INVENTORY_BY_LOCATION}*")

    logger.info("Cache de ubicaciones de almacenamiento invalidado")


class LocationViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar ubicaciones de almacenamiento.

    Permite a los administradores gestionar las ubicaciones donde se almacenan
    los productos en el sistema de inventario.
    """

    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_summary="Listar ubicaciones de almacenamiento",
        operation_description="Obtiene todas las ubicaciones de almacenamiento disponibles en el sistema",
        responses={
            200: LocationSerializer(many=True),
            403: openapi.Response(description="Sin permisos de administrador")
        },
        tags=storage_admin()
    )
    def list(self, request, *args, **kwargs):
        """Lista todas las ubicaciones de almacenamiento con cache."""

        # Intentar obtener del cache
        cached_response = cache_manager.get(CacheKeys.STORAGE_LOCATIONS_LIST)
        if cached_response is not None:
            logger.debug("Ubicaciones de almacenamiento obtenidas del cache")
            return Response(cached_response, status=status.HTTP_200_OK)

        # Si no está en cache, obtener de la base de datos
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        response_data = serializer.data

        # Guardar en cache con timeout largo ya que las ubicaciones cambian poco
        cache_manager.set(
            CacheKeys.STORAGE_LOCATIONS_LIST,
            response_data,
            timeout=CacheTimeouts.STATIC_DATA
        )

        logger.debug("Ubicaciones de almacenamiento guardadas en cache")
        return Response(response_data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Obtener ubicación específica",
        operation_description="Obtiene los detalles de una ubicación de almacenamiento específica",
        responses={
            200: LocationSerializer,
            404: openapi.Response(description="Ubicación no encontrada"),
            403: openapi.Response(description="Sin permisos de administrador")
        },
        tags=storage_admin()
    )
    def retrieve(self, request, *args, **kwargs):
        """Obtiene una ubicación específica con cache."""

        location_id = kwargs.get('pk')

        # Intentar obtener del cache
        cached_response = cache_manager.get(
            CacheKeys.STORAGE_LOCATION_DETAIL, location_id=location_id)
        if cached_response is not None:
            logger.debug(f"Ubicación {location_id} obtenida del cache")
            return Response(cached_response, status=status.HTTP_200_OK)

        # Si no está en cache, obtener de la base de datos
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)

            response_data = serializer.data

            # Guardar en cache
            cache_manager.set(
                CacheKeys.STORAGE_LOCATION_DETAIL,
                response_data,
                timeout=CacheTimeouts.STATIC_DATA,
                location_id=location_id
            )

            logger.debug(f"Ubicación {location_id} guardada en cache")
            return Response(response_data, status=status.HTTP_200_OK)

        except Location.DoesNotExist:
            return Response(
                {"detail": "No encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        operation_summary="Crear ubicación de almacenamiento",
        operation_description="Crea una nueva ubicación de almacenamiento en el sistema",
        request_body=LocationSerializer,
        responses={
            201: LocationSerializer,
            400: openapi.Response(description="Datos inválidos"),
            403: openapi.Response(description="Sin permisos de administrador")
        },
        tags=storage_admin()
    )
    def create(self, request, *args, **kwargs):
        """Crea una nueva ubicación e invalida cache."""
        response = super().create(request, *args, **kwargs)

        if response.status_code == status.HTTP_201_CREATED:
            _invalidate_storage_cache()
            logger.info(
                f"Nueva ubicación creada por usuario {request.user.id}")

        return response

    @swagger_auto_schema(
        operation_summary="Actualizar ubicación completa",
        operation_description="Actualiza todos los campos de una ubicación de almacenamiento",
        request_body=LocationSerializer,
        responses={
            200: LocationSerializer,
            400: openapi.Response(description="Datos inválidos"),
            404: openapi.Response(description="Ubicación no encontrada"),
            403: openapi.Response(description="Sin permisos de administrador")
        },
        tags=storage_admin()
    )
    def update(self, request, *args, **kwargs):
        """Actualiza una ubicación e invalida cache."""
        response = super().update(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            _invalidate_storage_cache()
            logger.info(
                f"Ubicación {kwargs.get('pk')} actualizada por usuario {request.user.id}")

        return response

    @swagger_auto_schema(
        operation_summary="Actualizar ubicación parcial",
        operation_description="Actualiza campos específicos de una ubicación de almacenamiento",
        request_body=LocationSerializer,
        responses={
            200: LocationSerializer,
            400: openapi.Response(description="Datos inválidos"),
            404: openapi.Response(description="Ubicación no encontrada"),
            403: openapi.Response(description="Sin permisos de administrador")
        },
        tags=storage_admin()
    )
    def partial_update(self, request, *args, **kwargs):
        """Actualiza parcialmente una ubicación e invalida cache."""
        response = super().partial_update(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            _invalidate_storage_cache()
            logger.info(
                f"Ubicación {kwargs.get('pk')} actualizada parcialmente por usuario {request.user.id}")

        return response

    @swagger_auto_schema(
        operation_summary="Eliminar ubicación",
        operation_description="Elimina una ubicación de almacenamiento del sistema",
        responses={
            204: openapi.Response(description="Ubicación eliminada exitosamente"),
            404: openapi.Response(description="Ubicación no encontrada"),
            403: openapi.Response(description="Sin permisos de administrador")
        },
        tags=storage_admin()
    )
    def destroy(self, request, *args, **kwargs):
        """Elimina una ubicación e invalida cache."""
        response = super().destroy(request, *args, **kwargs)

        if response.status_code == status.HTTP_204_NO_CONTENT:
            _invalidate_storage_cache()
            logger.info(
                f"Ubicación {kwargs.get('pk')} eliminada por usuario {request.user.id}")

        return response
        return super().destroy(request, *args, **kwargs)
