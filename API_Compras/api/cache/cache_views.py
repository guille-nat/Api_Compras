from rest_framework.decorators import api_view, permission_classes
from api.view_tags import cache_admin
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from api.cache.cache_utils import cache_manager, CacheKeys, CacheTimeouts
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging

logger = logging.getLogger(__name__)


@swagger_auto_schema(
    method='get',
    operation_summary="Obtener estadísticas de cache",
    operation_description="Obtiene estadísticas detalladas del sistema de cache Redis. Solo disponible para administradores.",
    responses={
        200: openapi.Response(
            description="Estadísticas de cache obtenidas exitosamente",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'cache_stats': openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'hits': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'misses': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'sets': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'deletes': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'total_requests': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'hit_rate_percent': openapi.Schema(type=openapi.TYPE_NUMBER)
                                }
                            ),
                            'redis_info': openapi.Schema(type=openapi.TYPE_OBJECT),
                            'cache_keys_summary': openapi.Schema(type=openapi.TYPE_OBJECT)
                        }
                    )
                }
            )
        ),
        403: openapi.Response(description="Sin permisos de administrador"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=cache_admin()
)
@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_cache_stats(request):
    """
    Obtiene estadísticas completas del sistema de cache.

    Esta vista proporciona información detallada sobre el rendimiento
    del cache, incluyendo estadísticas de hits/misses, información
    de Redis y resumen de claves cacheadas.

    Returns:
        Response: Estadísticas completas del cache
    """
    try:
        # Estadísticas básicas del cache manager
        cache_stats = cache_manager.get_stats()

        # Información de Redis
        redis_info = {}
        redis_keys_summary = {}

        try:
            from django.core.cache.backends.redis import RedisCache
            if isinstance(cache, RedisCache):
                redis_client = cache._cache.get_client(write=True)
                info = redis_client.info()

                redis_info = {
                    'redis_version': info.get('redis_version', 'N/A'),
                    'used_memory': info.get('used_memory', 0),
                    'used_memory_human': info.get('used_memory_human', 'N/A'),
                    'connected_clients': info.get('connected_clients', 0),
                    'total_commands_processed': info.get('total_commands_processed', 0),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0),
                    'uptime_in_seconds': info.get('uptime_in_seconds', 0)
                }

                # Resumen de claves por tipo
                keys = redis_client.keys("*")
                key_groups = {}

                for key in keys:
                    key_str = key.decode(
                        'utf-8') if isinstance(key, bytes) else str(key)
                    prefix = key_str.split(
                        ':')[0] if ':' in key_str else 'others'

                    if prefix not in key_groups:
                        key_groups[prefix] = 0
                    key_groups[prefix] += 1

                redis_keys_summary = {
                    'total_keys': len(keys),
                    'by_prefix': key_groups
                }

        except Exception as e:
            logger.warning(f"No se pudo obtener información de Redis: {e}")
            redis_info = {'error': 'Redis info no disponible'}

        # Configuración de timeouts
        cache_config = {
            'timeouts': {
                'static_data': CacheTimeouts.STATIC_DATA,
                'master_data': CacheTimeouts.MASTER_DATA,
                'product_data': CacheTimeouts.PRODUCT_DATA,
                'inventory_data': CacheTimeouts.INVENTORY_DATA,
                'analytics_data': CacheTimeouts.ANALYTICS_DATA,
                'user_data': CacheTimeouts.USER_DATA
            },
            'key_patterns': {
                'products': [
                    CacheKeys.PRODUCTS_LIST,
                    CacheKeys.PRODUCT_DETAIL,
                    CacheKeys.PRODUCTS_BY_CATEGORY,
                    CacheKeys.PRODUCTS_SEARCH
                ],
                'categories': [
                    CacheKeys.CATEGORIES_LIST,
                    CacheKeys.CATEGORY_DETAIL,
                    CacheKeys.CATEGORIES_TREE
                ],
                'inventory': [
                    CacheKeys.INVENTORY_LIST,
                    CacheKeys.INVENTORY_BY_PRODUCT,
                    CacheKeys.INVENTORY_BY_LOCATION,
                    CacheKeys.INVENTORY_STOCK
                ],
                'analytics': [
                    CacheKeys.ANALYTICS_SALES,
                    CacheKeys.ANALYTICS_PRODUCTS,
                    CacheKeys.ANALYTICS_REVENUE
                ]
            }
        }

        return Response({
            'success': True,
            'message': 'Estadísticas de cache obtenidas exitosamente',
            'data': {
                'cache_stats': cache_stats,
                'redis_info': redis_info,
                'cache_keys_summary': redis_keys_summary,
                'cache_config': cache_config
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error al obtener estadísticas de cache: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error al obtener estadísticas de cache',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    operation_summary="Limpiar cache por patrón",
    operation_description="Elimina claves de cache que coincidan con un patrón específico. Solo disponible para administradores.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'pattern': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Patrón de claves a eliminar (ej: 'products:*', 'categories:*')"
            ),
            'confirm': openapi.Schema(
                type=openapi.TYPE_BOOLEAN,
                description="Confirmación para proceder con la eliminación"
            )
        },
        required=['pattern', 'confirm']
    ),
    responses={
        200: openapi.Response(
            description="Cache limpiado exitosamente",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=True),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'pattern': openapi.Schema(type=openapi.TYPE_STRING),
                            'deleted_count': openapi.Schema(type=openapi.TYPE_INTEGER)
                        }
                    )
                }
            )
        ),
        400: openapi.Response(description="Patrón inválido o falta confirmación"),
        403: openapi.Response(description="Sin permisos de administrador"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=cache_admin()
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def clear_cache_pattern(request):
    """
    Limpia cache por patrón específico.

    Esta vista permite a los administradores limpiar selectivamente
    partes del cache usando patrones de claves.

    Request Body:
        pattern (str): Patrón de claves a eliminar
        confirm (bool): Confirmación requerida

    Returns:
        Response: Resultado de la operación de limpieza
    """
    try:
        pattern = request.data.get('pattern')
        confirm = request.data.get('confirm', False)

        if not pattern:
            return Response({
                'success': False,
                'message': 'El patrón es requerido',
                'error': 'Missing pattern parameter'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not confirm:
            return Response({
                'success': False,
                'message': 'Confirmación requerida para limpiar cache',
                'error': 'Confirmation required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validar patrones permitidos para seguridad
        allowed_patterns = [
            'products:*', 'categories:*', 'inventory:*', 'storage:*',
            'analytics:*', 'promotions:*', 'users:*'
        ]

        if pattern not in allowed_patterns and not pattern.startswith('api_compras:'):
            return Response({
                'success': False,
                'message': f'Patrón no permitido. Patrones válidos: {", ".join(allowed_patterns)}',
                'error': 'Invalid pattern'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Ejecutar limpieza
        deleted_count = cache_manager.delete_pattern(pattern)

        logger.info(
            f"Cache limpiado por admin {request.user.id}: patrón={pattern}, eliminadas={deleted_count}")

        return Response({
            'success': True,
            'message': f'Cache limpiado exitosamente. {deleted_count} claves eliminadas.',
            'data': {
                'pattern': pattern,
                'deleted_count': deleted_count
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error al limpiar cache por patrón: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error al limpiar cache',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    operation_summary="Limpiar todo el cache",
    operation_description="Elimina todas las claves del cache. Operación destructiva que requiere confirmación. Solo disponible para administradores.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'confirm': openapi.Schema(
                type=openapi.TYPE_BOOLEAN,
                description="Confirmación requerida para proceder"
            )
        },
        required=['confirm']
    ),
    responses={
        200: openapi.Response(description="Cache limpiado completamente"),
        400: openapi.Response(description="Falta confirmación"),
        403: openapi.Response(description="Sin permisos de administrador"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=cache_admin()
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def clear_all_cache(request):
    """
    Limpia todo el cache del sistema.

    Esta es una operación destructiva que elimina todas las claves
    del cache. Requiere confirmación explícita.

    Request Body:
        confirm (bool): Confirmación requerida

    Returns:
        Response: Resultado de la operación
    """
    try:
        confirm = request.data.get('confirm', False)

        if not confirm:
            return Response({
                'success': False,
                'message': 'Confirmación requerida para limpiar todo el cache',
                'error': 'Confirmation required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Limpiar cache
        cache.clear()
        cache_manager.clear_stats()

        logger.warning(
            f"TODO el cache fue limpiado por admin {request.user.id}")

        return Response({
            'success': True,
            'message': 'Todo el cache ha sido limpiado exitosamente',
            'data': {
                'action': 'clear_all',
                'stats_reset': True
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error al limpiar todo el cache: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error al limpiar cache',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    operation_summary="Precalentar cache",
    operation_description="Precarga el cache con datos comunes para mejorar el rendimiento. Solo disponible para administradores.",
    responses={
        200: openapi.Response(description="Cache precalentado exitosamente"),
        403: openapi.Response(description="Sin permisos de administrador"),
        500: openapi.Response(description="Error interno del servidor")
    },
    tags=cache_admin()
)
@api_view(['POST'])
@permission_classes([IsAdminUser])
def warm_up_cache(request):
    """
    Precalienta el cache con datos comunes.

    Esta vista realiza consultas a endpoints comunes para
    poblar el cache con datos frecuentemente solicitados.

    Returns:
        Response: Resultado del precalentamiento
    """
    try:
        from django.test.client import Client

        client = Client()
        warmed_endpoints = []
        errors = []

        # Endpoints para precalentar
        endpoints_to_warm = [
            {'url': '/api/v2/products', 'name': 'Productos'},
            {'url': '/api/v2/categories', 'name': 'Categorías públicas'},
        ]

        for endpoint in endpoints_to_warm:
            try:
                response = client.get(endpoint['url'])
                if response.status_code == 200:
                    warmed_endpoints.append(endpoint)
                else:
                    errors.append(
                        f"{endpoint['name']}: HTTP {response.status_code}")
            except Exception as e:
                errors.append(f"{endpoint['name']}: {str(e)}")

        logger.info(
            f"Cache precalentado por admin {request.user.id}: {len(warmed_endpoints)} endpoints")

        return Response({
            'success': True,
            'message': f'Cache precalentado exitosamente para {len(warmed_endpoints)} endpoints',
            'data': {
                'warmed_endpoints': [ep['name'] for ep in warmed_endpoints],
                'total_warmed': len(warmed_endpoints),
                'errors': errors
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error al precalentar cache: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error al precalentar cache',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
