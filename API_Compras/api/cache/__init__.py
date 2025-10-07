"""Package para funcionalidades de cache agrupadas.

Exporta los elementos principales para uso desde `api.cache`.
"""
from .cache_utils import (
    CacheManager,
    cache_manager,
    cached_view,
    invalidate_cache_on_save,
    CacheKeys,
    CacheTimeouts,
)
from .cache_views import (
    get_cache_stats,
    clear_cache_pattern,
    clear_all_cache,
    warm_up_cache,
)

__all__ = [
    'CacheManager', 'cache_manager', 'cached_view', 'invalidate_cache_on_save',
    'CacheKeys', 'CacheTimeouts',
    'get_cache_stats', 'clear_cache_pattern', 'clear_all_cache', 'warm_up_cache'
]
