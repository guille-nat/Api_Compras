from django.core.management.base import BaseCommand
from django.core.cache import cache
from api.cache import cache_manager, CacheKeys
import json


class Command(BaseCommand):
    help = 'Administra el cache de Redis - monitorear, limpiar y estadísticas'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['stats', 'clear', 'clear-pattern', 'keys', 'warm-up'],
            help='Acción a realizar con el cache'
        )
        parser.add_argument(
            '--pattern',
            type=str,
            help='Patrón para limpiar claves específicas (usar con clear-pattern)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar información detallada'
        )

    def handle(self, *args, **options):
        action = options['action']
        verbose = options['verbose']

        if action == 'stats':
            self.show_stats(verbose)
        elif action == 'clear':
            self.clear_cache(verbose)
        elif action == 'clear-pattern':
            pattern = options.get('pattern')
            if not pattern:
                self.stdout.write(
                    self.style.ERROR(
                        '--pattern es requerido para clear-pattern')
                )
                return
            self.clear_pattern(pattern, verbose)
        elif action == 'keys':
            self.list_keys(verbose)
        elif action == 'warm-up':
            self.warm_up_cache(verbose)

    def show_stats(self, verbose):
        """Muestra estadísticas del cache."""
        self.stdout.write(self.style.SUCCESS('=== ESTADÍSTICAS DE CACHE ==='))

        stats = cache_manager.get_stats()

        self.stdout.write(f"Hits: {stats['hits']}")
        self.stdout.write(f"Misses: {stats['misses']}")
        self.stdout.write(f"Sets: {stats['sets']}")
        self.stdout.write(f"Deletes: {stats['deletes']}")
        self.stdout.write(f"Total Requests: {stats['total_requests']}")
        self.stdout.write(f"Hit Rate: {stats['hit_rate_percent']}%")

        if verbose:
            self.stdout.write(
                "\n" + self.style.WARNING('=== INFORMACIÓN DETALLADA ==='))

            try:
                from django.core.cache.backends.redis import RedisCache
                if isinstance(cache, RedisCache):
                    redis_client = cache._cache.get_client(write=True)
                    info_raw = redis_client.info()
                    try:
                        info = dict(info_raw or {})
                    except Exception:
                        info = {}

                    self.stdout.write(
                        f"Redis Version: {info.get('redis_version', 'N/A')}")
                    self.stdout.write(
                        f"Used Memory: {info.get('used_memory_human', 'N/A')}")
                    self.stdout.write(
                        f"Keys Count: {info.get('db0', {}).get('keys', 0)}")
                    self.stdout.write(
                        f"Connected Clients: {info.get('connected_clients', 'N/A')}")

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f"No se pudo obtener info de Redis: {e}")
                )

    def clear_cache(self, verbose):
        """Limpia todo el cache."""
        self.stdout.write(self.style.WARNING('Limpiando TODO el cache...'))

        cache.clear()
        cache_manager.clear_stats()

        self.stdout.write(self.style.SUCCESS('Cache limpiado exitosamente'))

        if verbose:
            self.stdout.write("Estadísticas reiniciadas")

    def clear_pattern(self, pattern, verbose):
        """Limpia cache por patrón."""
        self.stdout.write(f"Limpiando claves que coincidan con: {pattern}")

        try:
            deleted_count = cache_manager.delete_pattern(pattern)

            if deleted_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f"{deleted_count} claves eliminadas")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "No se encontraron claves que coincidan")
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error al limpiar por patrón: {e}")
            )

    def list_keys(self, verbose):
        """Lista claves del cache (solo con Redis)."""
        self.stdout.write(self.style.SUCCESS('=== CLAVES DE CACHE ==='))

        try:
            from django.core.cache.backends.redis import RedisCache
            if not isinstance(cache, RedisCache):
                self.stdout.write(
                    self.style.WARNING(
                        "Listado de claves solo disponible con Redis")
                )
                return

            redis_client = cache._cache.get_client(write=True)
            keys_raw = redis_client.keys("*")
            try:
                keys = list(keys_raw or [])
            except Exception:
                keys = []

            if not keys:
                self.stdout.write("No hay claves en el cache")
                return

            key_groups = {}
            for key in keys:
                key_str = key.decode(
                    'utf-8') if isinstance(key, bytes) else str(key)
                prefix = key_str.split(':')[0] if ':' in key_str else 'otros'

                if prefix not in key_groups:
                    key_groups[prefix] = []
                key_groups[prefix].append(key_str)

            for prefix, prefix_keys in key_groups.items():
                self.stdout.write(
                    f"\n{prefix.upper()} ({len(prefix_keys)} claves):")

                if verbose:
                    for key in sorted(prefix_keys):
                        self.stdout.write(f"  {key}")
                else:
                    for key in sorted(prefix_keys)[:5]:
                        self.stdout.write(f"  {key}")
                    if len(prefix_keys) > 5:
                        self.stdout.write(
                            f"  ... y {len(prefix_keys) - 5} más")

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error al listar claves: {e}")
            )

    def warm_up_cache(self, verbose):
        """Pre-carga cache con datos comunes."""
        self.stdout.write(self.style.SUCCESS('Precalentando cache...'))

        try:
            from django.test.client import Client
            from django.contrib.auth import get_user_model

            client = Client()

            urls_to_warm = [
                '/api/v2/products',
                '/api/v2/categories',
            ]

            warmed_count = 0
            for url in urls_to_warm:
                try:
                    if verbose:
                        self.stdout.write(f"Precalentando: {url}")

                    response = client.get(url)
                    if response.status_code == 200:
                        warmed_count += 1

                except Exception as e:
                    if verbose:
                        self.stdout.write(
                            self.style.WARNING(f"Error en {url}: {e}")
                        )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Cache precalentado: {warmed_count} URLs")
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error al precalentar cache: {e}")
            )

    def warm_up_specific_cache_keys(self):
        """Pre-carga claves específicas de cache."""

        common_cache_operations = [
            (CacheKeys.CATEGORIES_LIST, {'public': True}),
            (CacheKeys.STORAGE_LOCATIONS_LIST, {}),
        ]

        for cache_key, params in common_cache_operations:
            try:

                cached_value = cache_manager.get(cache_key, **params)
                if cached_value is None:

                    pass
            except Exception:
                pass
