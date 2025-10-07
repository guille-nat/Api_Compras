from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from api.view_tags import categories_public, categories_admin
from .serializers import CategoryPrivateSerializer, CategoryPublicSerializer
from . import services, selectors
from django.shortcuts import get_object_or_404
from .models import Category
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from api.cache import cache_manager, CacheKeys, CacheTimeouts
from api.response_helpers import success_response, server_error_response
import logging
from rest_framework.pagination import PageNumberPagination
logger = logging.getLogger(__name__)

PAGINATION_PAGE_SIZE_CATEGORY = 10


def _invalidate_categories_cache():
    """
    Invalida el cache relacionado con categorías.

    Esta función se ejecuta después de crear, actualizar o eliminar categorías
    para asegurar que los datos en cache estén actualizados.
    """
    # Invalidar cache de categorías
    cache_manager.delete_pattern(f"{CacheKeys.CATEGORIES_LIST}*")
    cache_manager.delete_pattern(f"{CacheKeys.CATEGORIES_TREE}*")
    cache_manager.delete_pattern(f"{CacheKeys.CATEGORY_DETAIL}*")

    # También invalidar cache de productos por categoría ya que las categorías pueden haber cambiado
    cache_manager.delete_pattern(f"{CacheKeys.PRODUCTS_BY_CATEGORY}*")

    logger.info("Cache de categorías invalidado")


@swagger_auto_schema(
    method='get',
    operation_summary="Listar categorías (Admin)",
    operation_description="Obtiene todas las categorías del sistema con información completa. Solo disponible para administradores.",
    manual_parameters=[
        openapi.Parameter(
            'ordering',
            openapi.IN_QUERY,
            description="Campo por el cual ordenar. Usar '-' para orden descendente (ej: -name, created_at)",
            type=openapi.TYPE_STRING,
            required=False
        ),
        openapi.Parameter(
            'search',
            openapi.IN_QUERY,
            description="Buscar categorías por nombre o descripción",
            type=openapi.TYPE_STRING,
            required=False
        )
    ],
    responses={
        200: openapi.Response(
            description="Lista completa de categorías",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=CategoryPrivateSerializer
                    ),
                    'count': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        ),
        403: openapi.Response(description="Sin permisos de administrador"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=categories_admin()
)
@extend_schema(
    summary="Listar categorías (Admin)",
    description="Obtiene todas las categorías del sistema con información completa. Solo disponible para administradores.",
    parameters=[
        OpenApiParameter(name='ordering', required=False, location=OpenApiParameter.QUERY, type=OpenApiTypes.STR,
                         description="Campo por el cual ordenar. Use '-' para descendente (ej: -name)"),
        OpenApiParameter(name='search', required=False, location=OpenApiParameter.QUERY,
                         type=OpenApiTypes.STR, description="Buscar categorías por nombre o descripción"),
    ],
    responses={200: CategoryPrivateSerializer(many=True)},
    tags=categories_admin(),
)
@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_categories_admin(request):
    """
    Lista todas las categorías con información administrativa.

    Esta vista permite a los administradores acceder a información completa
    de todas las categorías del sistema, incluyendo datos privados como
    fechas de creación, modificación y estado interno.

    Returns:
        Response: Lista completa de categorías siguiendo el estándar de respuestas

    Raises:
        403: Usuario sin permisos de administrador
        500: Error interno del servidor o fallo en la consulta
    """
    try:
        # Generar clave de cache
        search = request.GET.get('search', '')
        ordering = request.GET.get('ordering', '')
        cache_key_params = {
            'admin': True,
            'search': search,
            'ordering': ordering
        }
        paginator = PageNumberPagination()
        paginator.page_size = PAGINATION_PAGE_SIZE_CATEGORY

        # Intentar obtener del cache
        cached_response = cache_manager.get(
            CacheKeys.CATEGORIES_LIST, **cache_key_params)
        if cached_response is not None:
            logger.debug("Categorías admin obtenidas del cache")
            return Response(cached_response, status=status.HTTP_200_OK)

        # Si no está en cache, obtener de la base de datos
        categories = selectors.list_categories_admin()

        # Aplicar paginación con manejo de errores para tests
        try:
            page_data = paginator.paginate_queryset(categories, request)
        except (TypeError, AttributeError):
            # Si falla con objetos mock/fake, convertir a lista
            categories = list(categories)
            page_data = paginator.paginate_queryset(categories, request)

        serializer = CategoryPrivateSerializer(page_data, many=True)
        response_data = paginator.get_paginated_response(serializer.data)

        # Formatear respuesta según estándar
        formatted_response = {
            "success": True,
            "message": "Categorías obtenidas exitosamente",
            "data": response_data.data
        }

        # Guardar en cache
        cache_manager.set(
            CacheKeys.CATEGORIES_LIST,
            formatted_response,
            timeout=CacheTimeouts.MASTER_DATA,
            **cache_key_params
        )

        logger.info(f"Admin {request.user.id} accessed categories list")
        return Response(formatted_response, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error listing admin categories: {str(e)}")
        return Response({
            "success": False,
            "message": "Error al obtener categorías",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    operation_summary="Crear categoría",
    operation_description="Crea una nueva categoría en el sistema. Solo disponible para administradores.",
    request_body=CategoryPrivateSerializer,
    responses={
        201: openapi.Response(
            description="Categoría creada exitosamente",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': CategoryPrivateSerializer
                }
            )
        ),
        400: openapi.Response(
            description="Datos inválidos",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=False),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        403: openapi.Response(description="Sin permisos de administrador"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=categories_admin()
)
@extend_schema(
    summary="Crear categoría",
    description="Crea una nueva categoría en el sistema. Solo disponible para administradores.",
    request=CategoryPrivateSerializer,
    responses={201: CategoryPrivateSerializer},
    tags=categories_admin(),
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_category(request):
    """
    Crea una nueva categoría en el sistema.

    Esta vista permite a los administradores crear nuevas categorías
    para organizar los productos del sistema.

    Request Body:
        CategoryPrivateSerializer: Datos de la categoría incluyendo nombre,
                                  descripción, estado y otros campos requeridos

    Returns:
        Response: Categoría creada siguiendo el estándar de respuestas

    Raises:
        400: Datos inválidos, nombre duplicado o campos requeridos faltantes
        403: Usuario sin permisos de administrador
        500: Error interno del servidor o fallo en la creación
    """
    try:
        serializer = CategoryPrivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = services.create_category(
            user=request.user,
            name=serializer.validated_data["name"]
        )

        # Invalidar cache de categorías después de crear
        _invalidate_categories_cache()

        logger.info(
            f"Category created successfully by admin {request.user.id}: {result['message']}")

        # Serializar la categoría creada para la respuesta
        category_data = CategoryPrivateSerializer(
            result["data"]).data

        return Response({
            "success": True,
            "message": result["message"],
            "data":  category_data
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(
            f"Error creating category by admin {request.user.id}: {str(e)}")
        return Response({
            "success": False,
            "message": "Error al crear categoría",
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='get',
    operation_summary="Obtener categoría específica (Admin)",
    operation_description="Obtiene los detalles completos de una categoría específica. Solo disponible para administradores.",
    manual_parameters=[
        openapi.Parameter(
            'id',
            openapi.IN_PATH,
            description="ID único de la categoría",
            type=openapi.TYPE_INTEGER,
            required=True
        )
    ],
    responses={
        200: openapi.Response(
            description="Detalles de la categoría",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': CategoryPrivateSerializer
                }
            )
        ),
        403: openapi.Response(description="Sin permisos de administrador"),
        404: openapi.Response(description="Categoría no encontrada"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=categories_admin()
)
@extend_schema(
    summary="Obtener categoría específica (Admin)",
    description="Obtiene los detalles completos de una categoría específica. Solo disponible para administradores.",
    parameters=[OpenApiParameter(name='id', required=True, location=OpenApiParameter.PATH,
                                 type=OpenApiTypes.INT, description='ID único de la categoría')],
    responses={200: CategoryPrivateSerializer},
    tags=categories_admin(),
)
@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_category_admin(request, pk):
    """
    Obtiene los detalles completos de una categoría específica.

    Esta vista permite a los administradores acceder a información
    detallada de una categoría incluyendo metadatos administrativos.

    Path Parameters:
        pk (int): ID único de la categoría a consultar

    Returns:
        Response: Detalles completos de la categoría siguiendo el estándar

    Raises:
        403: Usuario sin permisos de administrador
        404: Categoría no encontrada
        500: Error interno del servidor
    """
    try:
        category = get_object_or_404(Category, pk=pk)
        serializer = CategoryPrivateSerializer(category)
        logger.info(f"Admin {request.user.id} accessed category {pk}")
        return Response({"success": True,
                         "message": "Category retrieved successfully.",
                         "data": serializer.data}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error getting category {id}: {str(e)}")
        return Response({
            "success": False,
            "message": "Error al obtener categoría",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    methods=['put', 'patch'],
    operation_summary="Actualizar categoría",
    operation_description="Actualiza una categoría existente. PUT para actualización completa, PATCH para parcial. Solo disponible para administradores.",
    manual_parameters=[
        openapi.Parameter(
            'id',
            openapi.IN_PATH,
            description="ID único de la categoría a actualizar",
            type=openapi.TYPE_INTEGER,
            required=True
        )
    ],
    request_body=CategoryPrivateSerializer,
    responses={
        200: openapi.Response(
            description="Categoría actualizada exitosamente",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': CategoryPrivateSerializer
                }
            )
        ),
        400: openapi.Response(description="Datos inválidos"),
        403: openapi.Response(description="Sin permisos de administrador"),
        404: openapi.Response(description="Categoría no encontrada"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=categories_admin()
)
@extend_schema(
    summary="Actualizar categoría",
    description="Actualiza una categoría existente. PUT para actualización completa, PATCH para parcial. Solo disponible para administradores.",
    parameters=[OpenApiParameter(name='id', required=True, location=OpenApiParameter.PATH,
                                 type=OpenApiTypes.INT, description='ID único de la categoría a actualizar')],
    request=CategoryPrivateSerializer,
    responses={200: CategoryPrivateSerializer},
    tags=categories_admin(),
)
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminUser])
def update_category(request, pk):
    """
    Actualiza una categoría existente.

    Esta vista permite a los administradores modificar categorías existentes.
    Admite tanto actualización completa (PUT) como parcial (PATCH).

    Path Parameters:
        pk (int): ID único de la categoría a actualizar

    Request Body:
        CategoryPrivateSerializer: Datos de la categoría a actualizar.
                                  Para PATCH solo se requieren los campos a modificar.

    Returns:
        Response: Categoría actualizada siguiendo el estándar de respuestas

    Raises:
        400: Datos inválidos o nombre duplicado
        403: Usuario sin permisos de administrador
        404: Categoría no encontrada
        500: Error interno del servidor o fallo en la actualización
    """
    try:
        category = Category.objects.select_for_update().filter(id=pk).first()
        partial = request.method == 'PATCH'

        serializer = CategoryPrivateSerializer(
            category, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)

        # Solo se aplica servicio especial si se cambia el nombre
        if "name" in serializer.validated_data:
            result = services.rename_category(
                user=request.user,
                category=category,
                new_name=serializer.validated_data["name"]
            )

            logger.info(
                f"Category updated successfully by admin {request.user.id}: {result['message']}")

            # Serializar la categoría actualizada para la respuesta
            category_data = CategoryPrivateSerializer(
                result["data"]["category"]).data

            return Response({
                "success": True,
                "message": result["message"],
                "data": {
                    "category": category_data,
                    "old_name": result["data"]["old_name"],
                    "new_name": result["data"]["new_name"]
                }
            }, status=status.HTTP_200_OK)
        else:
            # Si no hay cambio de nombre, usar actualización estándar
            serializer.save()
            logger.info(f"Category {id} updated by admin {request.user.id}")

            return Response({
                "success": True,
                "message": "Categoría actualizada exitosamente",
                "data": {
                    "category": serializer.data
                }
            }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(
            f"Error updating category {id} by admin {request.user.id}: {str(e)}")
        return Response({
            "success": False,
            "message": "Error al actualizar categoría",
            "error": str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='delete',
    operation_summary="Eliminar categoría",
    operation_description="Elimina una categoría del sistema. Solo disponible para administradores.",
    manual_parameters=[
        openapi.Parameter(
            'id',
            openapi.IN_PATH,
            description="ID único de la categoría a eliminar",
            type=openapi.TYPE_INTEGER,
            required=True
        )
    ],
    responses={
        204: openapi.Response(
            description="Categoría eliminada exitosamente",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
                    'message': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        400: openapi.Response(
            description="No se puede eliminar categoría con productos asociados",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=False),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        403: openapi.Response(description="Sin permisos de administrador"),
        404: openapi.Response(description="Categoría no encontrada"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=categories_admin()
)
@extend_schema(
    summary="Eliminar categoría",
    description="Elimina una categoría del sistema. Solo disponible para administradores.",
    parameters=[OpenApiParameter(name='id', required=True, location=OpenApiParameter.PATH,
                                 type=OpenApiTypes.INT, description='ID único de la categoría a eliminar')],
    responses={204: None},
    tags=categories_admin(),
)
@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_category(request, pk):
    """
    Elimina una categoría del sistema.

    Esta vista permite a los administradores eliminar categorías que ya no
    son necesarias. No se permite eliminar categorías con productos asociados.

    Path Parameters:
        pk (int): ID único de la categoría a eliminar

    Returns:
        Response: Confirmación de eliminación

    Raises:
        400: Categoría tiene productos asociados y no se puede eliminar
        403: Usuario sin permisos de administrador
        404: Categoría no encontrada
        500: Error interno del servidor

    Warning:
        Esta operación es irreversible. Verificar que la categoría
        no tenga productos asociados antes de eliminar.
    """
    try:
        category = get_object_or_404(Category, pk=pk)
        category_name = category.name

        # Verificar si tiene productos asociados (ejemplo de validación)
        if hasattr(category, 'product_set') and category.product_set.exists():
            logger.warning(
                f"Admin {request.user.id} tried to delete category {pk} with associated products")
            return Response({
                "success": False,
                "message": f"No se puede eliminar la categoría '{category_name}' porque tiene productos asociados"
            }, status=status.HTTP_400_BAD_REQUEST)

        category.delete()
        logger.info(
            f"Category '{category_name}' deleted successfully by admin {request.user.id}")

        return Response({
            "success": True,
            "message": f"Categoría '{category_name}' eliminada exitosamente"
        }, status=status.HTTP_204_NO_CONTENT)

    except Exception as e:
        logger.error(
            f"Error deleting category {id} by admin {request.user.id}: {str(e)}")
        return Response({
            "success": False,
            "message": "Error al eliminar categoría",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    operation_summary="Listar categorías públicas",
    operation_description="Obtiene todas las categorías activas disponibles para usuarios públicos.",
    responses={
        200: openapi.Response(
            description="Lista de categorías públicas",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=CategoryPublicSerializer
                    ),
                    'count': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        ),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=categories_public()
)
@extend_schema(
    summary="Listar categorías públicas",
    description="Obtiene todas las categorías activas disponibles para usuarios públicos.",
    responses={200: CategoryPublicSerializer(many=True)},
    tags=categories_public(),
)
@api_view(['GET'])
@permission_classes([AllowAny])
def list_categories_public(request):
    """
    Lista todas las categorías activas para acceso público.

    Esta vista permite a cualquier usuario (incluso sin autenticar)
    consultar las categorías activas disponibles en el sistema.

    Returns:
        Response: Lista de categorías públicas siguiendo el estándar de respuestas

    Raises:
        500: Error interno del servidor o fallo en la consulta
    """
    try:
        page_number = request.query_params.get('page', 1)
        cache_key_params = {'public': True, 'page': page_number}
        # Intentar obtener del cache
        cached_response = cache_manager.get(
            CacheKeys.CATEGORIES_LIST, **cache_key_params)
        if cached_response is not None:
            logger.debug("Categorías públicas obtenidas del cache")
            return Response(cached_response, status=status.HTTP_200_OK)

        # Si no está en cache, obtener de la base de datos
        categories = selectors.list_categories_public()

        # Algunos selectores pueden devolver iterables que no implementan
        # __len__ o count (p.ej. objetos falsos en tests). Para asegurar
        # compatibilidad, convertir a lista si es necesario
        try:
            # Intentar usar directamente con el paginador
            paginator = PageNumberPagination()
            paginator.page_size = PAGINATION_PAGE_SIZE_CATEGORY
            page_data = paginator.paginate_queryset(categories, request)
        except (TypeError, AttributeError):
            # Si falla, convertir a lista y reintentar
            categories = list(categories)
            paginator = PageNumberPagination()
            paginator.page_size = PAGINATION_PAGE_SIZE_CATEGORY
            page_data = paginator.paginate_queryset(categories, request)

        serialized_data = CategoryPublicSerializer(page_data, many=True).data

        # Devolver response ya paginada con formato estándar
        response = paginator.get_paginated_response(serialized_data)

        # Formatear según estándar de respuesta
        formatted_response = {
            "success": True,
            "message": "Categorías públicas obtenidas exitosamente",
            "data": response.data
        }

        # Cache the formatted response data
        try:
            cache_manager.set(
                CacheKeys.CATEGORIES_LIST,
                formatted_response,
                timeout=CacheTimeouts.STATIC_DATA,
                **cache_key_params
            )
            logger.debug("Categorías públicas guardadas en cache")
        except Exception:
            # Cache failures should not break the response
            logger.debug("No se pudo guardar cache de categorías públicas")

        return Response(formatted_response, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error listing public categories: {str(e)}")
        return Response({
            "success": False,
            "message": "Error al obtener categorías públicas",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    operation_summary="Obtener categoría específica (Público)",
    operation_description="Obtiene los detalles públicos de una categoría específica.",
    manual_parameters=[
        openapi.Parameter(
            'id',
            openapi.IN_PATH,
            description="ID único de la categoría a consultar",
            type=openapi.TYPE_INTEGER,
            required=True
        )
    ],
    responses={
        200: openapi.Response(
            description="Detalles públicos de la categoría",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': CategoryPublicSerializer
                }
            )
        ),
        404: openapi.Response(description="Categoría no encontrada o inactiva"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=categories_public()
)
@extend_schema(
    summary="Obtener categoría específica (Público)",
    description="Obtiene los detalles públicos de una categoría específica.",
    parameters=[
        OpenApiParameter(name='id', required=True, location=OpenApiParameter.PATH,
                         type=OpenApiTypes.INT, description='ID único de la categoría a consultar')
    ],
    responses={200: CategoryPublicSerializer},
    tags=categories_public(),
)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_category_public(request, id):
    """
    Obtiene los detalles públicos de una categoría específica.

    Esta vista permite a cualquier usuario consultar información básica
    de una categoría activa sin exponer datos administrativos.

    Path Parameters:
        pk (int): ID único de la categoría a consultar

    Returns:
        Response: Detalles públicos de la categoría siguiendo el estándar

    Raises:
        404: Categoría no encontrada o inactiva
        500: Error interno del servidor
    """
    try:
        category = get_object_or_404(Category, pk=id)
        serializer = CategoryPublicSerializer(category)
        return success_response("Category retrieved successfully.", serializer.data)
    except Exception as e:
        logger.error(f"Error getting public category {id}: {str(e)}")
        return server_error_response("Error al obtener categoría pública")


@swagger_auto_schema(
    method='get',
    operation_summary="Categorías con promociones activas",
    operation_description="Obtiene las categorías que tienen promociones activas aplicadas.",
    responses={
        200: openapi.Response(
            description="Lista de categorías con promociones activas",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'category': CategoryPublicSerializer,
                                'active_promotions': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT)
                                ),
                                'promotion_count': openapi.Schema(type=openapi.TYPE_INTEGER)
                            }
                        )
                    ),
                    'count': openapi.Schema(type=openapi.TYPE_INTEGER)
                }
            )
        ),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=categories_public()
)
@extend_schema(
    summary="Categorías con promociones activas",
    description="Obtiene las categorías que tienen promociones activas aplicadas.",
    responses={200: OpenApiTypes.OBJECT},
    tags=categories_public(),
)
@api_view(['GET'])
@permission_classes([AllowAny])
def get_categories_with_promotions(request):
    """
    Obtiene las categorías que tienen promociones activas.

    Esta vista permite a cualquier usuario consultar las categorías
    que actualmente tienen promociones activas aplicadas, junto con
    información básica de las promociones.

    Returns:
        Response: Lista de categorías con promociones activas siguiendo
                 el estándar de respuestas

    Raises:
        500: Error interno del servidor o fallo en la consulta

    Note:
        Solo se muestran categorías activas con al menos una promoción
        vigente en el momento de la consulta.
    """
    try:
        result = services.get_all_categories_with_promotions()
        categories = result["data"]

        # Instancia de paginador
        paginator = PageNumberPagination()
        paginator.page_size = PAGINATION_PAGE_SIZE_CATEGORY

        # Paginar la lista en memoria
        page = paginator.paginate_queryset(categories, request)

        return paginator.get_paginated_response({
            "success": True,
            "message": result["message"],
            "data": page
        })

    except Exception as e:
        logger.error(f"Error obteniendo categorías con promociones: {str(e)}")
        return Response({
            "success": False,
            "message": "Error al obtener categorías con promociones",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
