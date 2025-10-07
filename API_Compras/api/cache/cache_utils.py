from django.core.cache import cache
from django.conf import settings
from functools import wraps
import hashlib
import json
import logging
from typing import Any, Optional, Dict, List, Callable
from datetime import timedelta

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Gestor centralizado de cache para el sistema.

    Esta clase proporciona una interfaz uniforme para el manejo de cache
    con funciones de logging, invalidación inteligente y métricas.

    Args:
        default_timeout (int): Tiempo de expiración por defecto en segundos.
        prefix (str): Prefijo para todas las claves de cache.
    """

    def __init__(self, default_timeout: int = 3600, prefix: str = "api_compras"):
        self.default_timeout = default_timeout
        self.prefix = prefix
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }

    def _get_key(self, key: str) -> str:
        """
        Genera una clave de cache con prefijo.

        Args:
            key (str): Clave base del cache.

        Returns:
            str: Clave con prefijo aplicado.
        """
        return f"{self.prefix}:{key}"

    def _generate_cache_key(self, base_key: str, **kwargs) -> str:
        """
        Genera una clave de cache única basada en parámetros.

        Args:
            base_key (str): Clave base del cache.
            **kwargs: Parámetros adicionales para generar la clave.

        Returns:
            str: Clave de cache única.
        """
        if kwargs:
            # Ordenar los kwargs para asegurar consistencia
            sorted_params = sorted(kwargs.items())
            param_string = json.dumps(sorted_params, sort_keys=True)
            hash_suffix = hashlib.md5(param_string.encode()).hexdigest()[:8]
            cache_key = f"{base_key}:{hash_suffix}"
        else:
            cache_key = base_key

        return self._get_key(cache_key)

    def get(self, key: str, **kwargs) -> Optional[Any]:
        """
        Obtiene un valor del cache.

        Args:
            key (str): Clave base del cache.
            **kwargs: Parámetros para generar la clave completa.

        Returns:
            Optional[Any]: Valor del cache o None si no existe.
        """
        cache_key = self._generate_cache_key(key, **kwargs)
        value = cache.get(cache_key)

        if value is not None:
            self.cache_stats['hits'] += 1
            logger.debug(f"Cache HIT para clave: {cache_key}")
        else:
            self.cache_stats['misses'] += 1
            logger.debug(f"Cache MISS para clave: {cache_key}")

        return value

    def set(self, key: str, value: Any, timeout: Optional[int] = None, **kwargs) -> bool:
        """
        Establece un valor en el cache.

        Args:
            key (str): Clave base del cache.
            value (Any): Valor a almacenar.
            timeout (Optional[int]): Tiempo de expiración en segundos.
            **kwargs: Parámetros para generar la clave completa.

        Returns:
            bool: True si se estableció correctamente.
        """
        cache_key = self._generate_cache_key(key, **kwargs)
        timeout = timeout or self.default_timeout

        try:
            cache.set(cache_key, value, timeout)
            # Django cache.set() no siempre retorna True/False explícitamente
            # Verificamos que se guardó correctamente intentando obtenerlo
            verification = cache.get(cache_key)
            if verification is not None:
                self.cache_stats['sets'] += 1
                logger.debug(
                    f"Cache SET para clave: {cache_key}, timeout: {timeout}s")
                return True
            else:
                logger.warning(
                    f"No se pudo verificar el guardado del cache para {cache_key}")
                return False
        except Exception as e:
            logger.error(
                f"Error al establecer cache para {cache_key}: {str(e)}")
            return False

    def delete(self, key: str, **kwargs) -> bool:
        """
        Elimina un valor del cache.

        Args:
            key (str): Clave base del cache.
            **kwargs: Parámetros para generar la clave completa.

        Returns:
            bool: True si se eliminó correctamente.
        """
        cache_key = self._generate_cache_key(key, **kwargs)

        try:
            # Verificar si la clave existe antes de eliminar
            exists = cache.get(cache_key) is not None
            result = cache.delete(cache_key)

            # Si la clave existía o Django retorna True, consideramos exitoso
            if exists or result:
                self.cache_stats['deletes'] += 1
                logger.debug(f"Cache DELETE para clave: {cache_key}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error al eliminar cache para {cache_key}: {str(e)}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Elimina todas las claves que coincidan con un patrón.

        Args:
            pattern (str): Patrón de búsqueda (usando wildcards de Redis).

        Returns:
            int: Número de claves eliminadas.
        """
        try:
            full_pattern = self._get_key(pattern)
            # Use duck-typing: if the cache backend exposes delete_pattern, call it.
            if hasattr(cache, 'delete_pattern') and callable(getattr(cache, 'delete_pattern')):
                deleted_count = cache.delete_pattern(full_pattern)
                # Some backends may return None; normalize to int
                deleted_count = int(deleted_count or 0)
                self.cache_stats['deletes'] += deleted_count
                logger.info(
                    f"Cache DELETE_PATTERN para patrón: {full_pattern}, eliminadas: {deleted_count}")
                return deleted_count
            else:
                # Fallback: si el backend no implementa delete_pattern, intentar limpiar el cache completo
                # Esto es útil en entornos de testing (LocMemCache) donde no hay soporte de patrones.
                if hasattr(cache, 'clear') and callable(getattr(cache, 'clear')):
                    try:
                        cache.clear()
                        logger.info(
                            "Backend de cache no soporta delete_pattern; se llamó a cache.clear() como fallback")
                    except Exception:
                        logger.warning(
                            "No se pudo ejecutar cache.clear() como fallback para delete_pattern")
                else:
                    logger.warning(
                        "delete_pattern solo está disponible con algunos backends (ej. Redis) o no está implementado")
                return 0
        except Exception as e:
            logger.error(f"Error al eliminar por patrón {pattern}: {str(e)}")
            return 0

    def get_stats(self) -> Dict[str, int]:
        """
        Obtiene estadísticas de uso del cache.

        Returns:
            Dict[str, int]: Diccionario con estadísticas de cache.
        """
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (
            self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        return {
            **self.cache_stats,
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2)
        }

    def clear_stats(self) -> None:
        """Limpia las estadísticas de cache."""
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }


# Instancia global del gestor de cache
cache_manager = CacheManager()


def cached_view(timeout: int = 3600, key_prefix: str = "view"):
    """
    Decorador para cachear vistas de Django REST Framework.

    Args:
        timeout (int): Tiempo de expiración del cache en segundos.
        key_prefix (str): Prefijo para la clave de cache.

    Returns:
        Callable: Decorador para vistas.

    Example:
        @cached_view(timeout=1800, key_prefix="products")
        @api_view(['GET'])
        def get_products(request):
            # Vista que será cacheada
            pass
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Generar clave de cache basada en la URL, parámetros de query y usuario
            cache_key_parts = [
                key_prefix,
                request.path,
                str(sorted(request.GET.items())),
                str(request.user.id if request.user.is_authenticated else 'anonymous')
            ]
            cache_key = hashlib.md5(
                '|'.join(cache_key_parts).encode()).hexdigest()

            # Intentar obtener del cache
            cached_response = cache_manager.get(cache_key)
            if cached_response is not None:
                logger.debug(f"Vista cacheada servida para: {request.path}")
                return cached_response

            # Ejecutar vista y cachear resultado
            response = view_func(request, *args, **kwargs)

            # Solo cachear respuestas exitosas
            if hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                cache_manager.set(cache_key, response, timeout)
                logger.debug(f"Vista cacheada guardada para: {request.path}")

            return response
        return wrapper
    return decorator


def invalidate_cache_on_save(cache_keys: List[str]):
    """
    Decorador para invalidar cache cuando se guarda un modelo.

    Args:
        cache_keys (List[str]): Lista de patrones de clave a invalidar.

    Returns:
        Callable: Decorador para modelos.

    Example:
        @invalidate_cache_on_save(['products:*', 'categories:*'])
        class Product(models.Model):
            pass
    """
    def decorator(model_class):
        original_save = model_class.save
        original_delete = model_class.delete

        def new_save(self, *args, **kwargs):
            result = original_save(self, *args, **kwargs)
            for pattern in cache_keys:
                cache_manager.delete_pattern(pattern)
            logger.info(
                f"Cache invalidado para patrones: {cache_keys} por save de {model_class.__name__}")
            return result

        def new_delete(self, *args, **kwargs):
            result = original_delete(self, *args, **kwargs)
            for pattern in cache_keys:
                cache_manager.delete_pattern(pattern)
            logger.info(
                f"Cache invalidado para patrones: {cache_keys} por delete de {model_class.__name__}")
            return result

        model_class.save = new_save
        model_class.delete = new_delete
        return model_class

    return decorator


# Constantes para claves de cache comunes
class CacheKeys:
    """Constantes para claves de cache del sistema."""

    # Productos
    PRODUCTS_LIST = "products:list"
    PRODUCT_DETAIL = "products:detail"
    PRODUCTS_BY_CATEGORY = "products:category"
    PRODUCTS_SEARCH = "products:search"

    # Categorías
    CATEGORIES_LIST = "categories:list"
    CATEGORY_DETAIL = "categories:detail"
    CATEGORIES_TREE = "categories:tree"

    # Inventario
    INVENTORY_LIST = "inventory:list"
    INVENTORY_BY_PRODUCT = "inventory:product"
    INVENTORY_BY_LOCATION = "inventory:location"
    INVENTORY_STOCK = "inventory:stock"

    # Storage Locations
    STORAGE_LOCATIONS_LIST = "storage:list"
    STORAGE_LOCATION_DETAIL = "storage:detail"

    # Analytics
    ANALYTICS_SALES = "analytics:sales"
    ANALYTICS_PRODUCTS = "analytics:products"
    ANALYTICS_REVENUE = "analytics:revenue"

    # Promociones
    PROMOTIONS_ACTIVE = "promotions:active"
    PROMOTIONS_BY_PRODUCT = "promotions:product"


# Configuraciones de timeout específicas por tipo de datos
class CacheTimeouts:
    """Tiempos de expiración de cache recomendados por tipo de datos."""

    STATIC_DATA = 24 * 3600  # 24 horas - Para datos que cambian muy poco
    MASTER_DATA = 6 * 3600   # 6 horas - Para datos maestros como categorías
    PRODUCT_DATA = 3600      # 1 hora - Para datos de productos
    # 5 minutos - Para datos de inventario (cambian frecuentemente)
    INVENTORY_DATA = 300
    ANALYTICS_DATA = 1800    # 30 minutos - Para reportes y analytics
    USER_DATA = 900          # 15 minutos - Para datos específicos de usuario
