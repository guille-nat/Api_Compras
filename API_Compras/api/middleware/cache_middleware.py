import time
import logging
from django.utils.deprecation import MiddlewareMixin
from api.cache import cache_manager


logger = logging.getLogger(__name__)


class CacheMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware para monitorear el rendimiento del cache en las requests.

    Este middleware registra estadísticas de cache por request y puede
    agregar headers informativos en modo DEBUG.
    """

    def process_request(self, request):
        """Inicializa el tracking de cache para la request."""
        request.cache_start_time = time.time()
        request.cache_start_stats = cache_manager.get_stats().copy()
        return None

    def process_response(self, request, response):
        """Procesa la respuesta y calcula métricas de cache."""
        if not hasattr(request, 'cache_start_time'):
            return response

        processing_time = time.time() - request.cache_start_time

        end_stats = cache_manager.get_stats()
        start_stats = request.cache_start_stats

        cache_hits = end_stats['hits'] - start_stats['hits']
        cache_misses = end_stats['misses'] - start_stats['misses']
        cache_sets = end_stats['sets'] - start_stats['sets']
        cache_deletes = end_stats['deletes'] - start_stats['deletes']

        if cache_hits > 0 or cache_misses > 0 or cache_sets > 0 or cache_deletes > 0:
            logger.info(
                f"Cache activity for {request.method} {request.path}: "
                f"hits={cache_hits}, misses={cache_misses}, "
                f"sets={cache_sets}, deletes={cache_deletes}, "
                f"processing_time={processing_time:.3f}s"
            )

        from django.conf import settings
        if settings.DEBUG:
            response['X-Cache-Hits'] = str(cache_hits)
            response['X-Cache-Misses'] = str(cache_misses)
            response['X-Cache-Sets'] = str(cache_sets)
            response['X-Cache-Processing-Time'] = f"{processing_time:.3f}"

            if cache_hits > 0 and cache_misses == 0 and cache_sets == 0:
                response['X-Cache-Status'] = 'HIT'
            elif cache_misses > 0 and cache_hits == 0:
                response['X-Cache-Status'] = 'MISS'
            else:
                response['X-Cache-Status'] = 'MIXED'

        return response


class CacheInvalidationMiddleware(MiddlewareMixin):
    """
    Middleware para invalidación automática de cache en operaciones específicas.

    Este middleware identifica operaciones que deberían invalidar cache
    y ejecuta la invalidación apropiada.
    """

    def process_response(self, request, response):
        """Invalida cache según el tipo de operación realizada."""

        if response.status_code not in [200, 201, 204]:
            return response

        method = request.method
        path = request.path

        if ('products' in path and method in ['POST', 'PUT', 'PATCH', 'DELETE']):
            self._invalidate_products_cache()

        elif ('categories' in path and method in ['POST', 'PUT', 'PATCH', 'DELETE']):
            self._invalidate_categories_cache()

        elif ('inventory' in path and method in ['POST', 'PUT', 'PATCH', 'DELETE']):
            self._invalidate_inventory_cache()

        elif ('storage' in path and method in ['POST', 'PUT', 'PATCH', 'DELETE']):
            self._invalidate_storage_cache()

        elif (('purchases' in path or 'sales' in path) and method in ['POST', 'PUT', 'PATCH', 'DELETE']):
            self._invalidate_analytics_cache()

        return response

    def _invalidate_products_cache(self):
        """Invalida cache relacionado con productos."""
    from api.cache import CacheKeys
    cache_manager.delete_pattern(f"{CacheKeys.PRODUCTS_LIST}*")
    cache_manager.delete_pattern(f"{CacheKeys.PRODUCTS_BY_CATEGORY}*")
    cache_manager.delete_pattern(f"{CacheKeys.PRODUCTS_SEARCH}*")
    cache_manager.delete_pattern(f"{CacheKeys.PRODUCT_DETAIL}*")
    logger.debug("Cache de productos invalidado por middleware")

    def _invalidate_categories_cache(self):
        """Invalida cache relacionado con categorías."""
    from api.cache import CacheKeys
    cache_manager.delete_pattern(f"{CacheKeys.CATEGORIES_LIST}*")
    cache_manager.delete_pattern(f"{CacheKeys.CATEGORIES_TREE}*")
    cache_manager.delete_pattern(f"{CacheKeys.CATEGORY_DETAIL}*")
    cache_manager.delete_pattern(f"{CacheKeys.PRODUCTS_BY_CATEGORY}*")
    logger.debug("Cache de categorías invalidado por middleware")

    def _invalidate_inventory_cache(self):
        """Invalida cache relacionado con inventario."""
    from api.cache import CacheKeys
    cache_manager.delete_pattern(f"{CacheKeys.INVENTORY_LIST}*")
    cache_manager.delete_pattern(f"{CacheKeys.INVENTORY_BY_PRODUCT}*")
    cache_manager.delete_pattern(f"{CacheKeys.INVENTORY_BY_LOCATION}*")
    cache_manager.delete_pattern(f"{CacheKeys.INVENTORY_STOCK}*")
    # También productos (el stock puede haber cambiado)
    cache_manager.delete_pattern(f"{CacheKeys.PRODUCTS_LIST}*")
    logger.debug("Cache de inventario invalidado por middleware")

    def _invalidate_storage_cache(self):
        """Invalida cache relacionado con ubicaciones de almacenamiento."""
    from api.cache import CacheKeys
    cache_manager.delete_pattern(f"{CacheKeys.STORAGE_LOCATIONS_LIST}*")
    cache_manager.delete_pattern(f"{CacheKeys.STORAGE_LOCATION_DETAIL}*")
    cache_manager.delete_pattern(f"{CacheKeys.INVENTORY_BY_LOCATION}*")
    logger.debug("Cache de ubicaciones invalidado por middleware")

    def _invalidate_analytics_cache(self):
        """Invalida cache relacionado con analytics."""
    from api.cache import CacheKeys
    cache_manager.delete_pattern(f"{CacheKeys.ANALYTICS_SALES}*")
    cache_manager.delete_pattern(f"{CacheKeys.ANALYTICS_PRODUCTS}*")
    cache_manager.delete_pattern(f"{CacheKeys.ANALYTICS_REVENUE}*")
    logger.debug("Cache de analytics invalidado por middleware")
