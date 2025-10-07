# 🚀 Sistema de Cache Redis - API Compras

## 📋 Descripción

Este documento describe la implementación completa del sistema de cache Redis para la API de Compras, diseñado para mejorar significativamente el rendimiento de la aplicación mediante el almacenamiento en memoria de datos frecuentemente consultados.

## 🏗️ Arquitectura del Cache

### Componentes Principales

1. **CacheManager** (`api/cache/cache_utils.py`) — se recomienda importar con `from api.cache import cache_manager, CacheKeys, CacheTimeouts`
   - Gestor centralizado de operaciones de cache
   - Manejo de claves con parámetros
   - Logging y estadísticas automáticas
   - Invalidación inteligente por patrones

2. **Middleware de Cache** (`api/middleware/cache_middleware.py`)
   - Monitoreo de rendimiento por request
   - Invalidación automática basada en operaciones
   - Headers informativos en modo DEBUG

3. **Vistas de Administración** (`api/cache/cache_views.py`) — se recomienda importar con `from api.cache import get_cache_stats, clear_cache_pattern, clear_all_cache, warm_up_cache`
   - Dashboard de estadísticas
   - Limpieza selectiva y total
   - Precalentamiento de cache

4. **Comando de Gestión** (`api/management/commands/cache_admin.py`)
   - Administración desde terminal
   - Monitoreo y mantenimiento
   - Precalentamiento automático

## 🔧 Configuración

### Redis Setup

El cache está configurado en `settings.py` con **fallback inteligente**:

```python
# Función para verificar disponibilidad de Redis
def is_redis_available():
    """
    Prueba la conexión a Redis con autenticación.
    Solo ejecuta el test una vez por proceso Django.
    """
    global _redis_test_done, _redis_available
    
    if _redis_test_done:
        return _redis_available
    
    try:
        import redis
        if REDIS_PASS:
            client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASS,
                socket_connect_timeout=1,
                socket_timeout=1,
                retry_on_timeout=False,
                db=1
            )
        client.ping()
        _redis_available = True
        print("✅ Redis conectado exitosamente - usando Redis como cache")
    except Exception as e:
        _redis_available = False
        print(f"⚠️  Redis no disponible ({e}), usando cache en memoria local")
    finally:
        _redis_test_done = True
    
    return _redis_available

# Configuración condicional de cache
if is_redis_available():
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"redis://:{REDIS_PASS}@{REDIS_HOST}:{REDIS_PORT}/1",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "IGNORE_EXCEPTIONS": True,  # Fallback en caso de errores
            }
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'sistema-compras-cache',
        }
    }
```

### Configuración de Docker

Redis está configurado en `docker-compose.yml`:

```yaml
redis:
  container_name: redis_cache
  image: redis:7-alpine
  ports:
    - "6379:6379"
  environment:
    - REDIS_PASSWORD=tu-password-redis-seguro
  volumes:
    - redis_data:/data
    - ./redis/redis.conf:/usr/local/etc/redis/redis.conf
  command: 
    - redis-server
    - /usr/local/etc/redis/redis.conf
    - --requirepass
    - tu-password-redis-seguro
  healthcheck:
    test: ["CMD", "redis-cli", "-a", "tu-password-redis-seguro", "ping"]
    interval: 5s
    timeout: 2s
    retries: 5
```

### Configuración redis.conf

**CRÍTICO**: El archivo `redis/redis.conf` fue corregido para permitir conexiones entre contenedores:

```properties
# ANTES (No funcionaba)
bind 127.0.0.1 ::1

# DESPUÉS (Corregido)
bind 0.0.0.0
protected-mode no
```

**Características implementadas**:

- **Networking correcto**: `bind 0.0.0.0` para permitir conexiones entre contenedores
- **Seguridad**: Autenticación con contraseña obligatoria
- **Persistencia**: Modo AOF habilitado con sincronización cada segundo
- **Optimización**: Política de evicción LRU con límite de 512MB
- **Monitoreo**: Health checks automáticos cada 5 segundos

## 📊 Tipos de Cache Implementados

### 1. Cache de Productos

- **Listado completo**: Cache de 1 hora
- **Búsquedas filtradas**: Cache de 30 minutos
- **Por categoría**: Cache de 1 hora
- **Invalidación**: Al crear/actualizar/eliminar productos

### 2. Cache de Categorías

- **Lista pública**: Cache de 24 horas
- **Lista admin**: Cache de 6 horas
- **Invalidación**: Al modificar categorías

### 3. Cache de Inventario

- **Registros de inventario**: Cache de 5 minutos
- **Por producto/ubicación**: Cache específico
- **Invalidación**: Al realizar movimientos de stock

### 4. Cache de Ubicaciones

- **Lista de ubicaciones**: Cache de 24 horas
- **Detalles específicos**: Cache de 24 horas
- **Invalidación**: Al modificar ubicaciones

### 5. Cache de Analytics

- **Reportes estadísticos**: Cache de 30 minutos
- **Productos más vendidos**: Cache de 30 minutos
- **No cachea archivos Excel/gráficos**

## ⏱️ Timeouts Configurados

```python
class CacheTimeouts:
    STATIC_DATA = 24 * 3600      # 24 horas - Datos estáticos
    MASTER_DATA = 6 * 3600       # 6 horas - Datos maestros
    PRODUCT_DATA = 3600          # 1 hora - Datos de productos
    INVENTORY_DATA = 300         # 5 minutos - Datos de inventario
    ANALYTICS_DATA = 1800        # 30 minutos - Reportes
    USER_DATA = 900              # 15 minutos - Datos de usuario
```

## 🔑 Claves de Cache

### Patrones de Claves

```python
class CacheKeys:
    # Productos
    PRODUCTS_LIST = "products:list"
    PRODUCT_DETAIL = "products:detail"
    PRODUCTS_BY_CATEGORY = "products:category"
    PRODUCTS_SEARCH = "products:search"
    
    # Categorías
    CATEGORIES_LIST = "categories:list"
    CATEGORY_DETAIL = "categories:detail"
    
    # Inventario
    INVENTORY_LIST = "inventory:list"
    INVENTORY_BY_PRODUCT = "inventory:product"
    INVENTORY_BY_LOCATION = "inventory:location"
    
    # Analytics
    ANALYTICS_SALES = "analytics:sales"
    ANALYTICS_PRODUCTS = "analytics:products"
```

## 🚀 Uso del Sistema

### En Vistas

```python
from api.cache_utils import cache_manager, CacheKeys, CacheTimeouts

# Obtener del cache
cached_data = cache_manager.get(CacheKeys.PRODUCTS_LIST, category_id=1)
if cached_data is not None:
    return Response(cached_data)

# Guardar en cache
response_data = {"success": True, "data": products}
cache_manager.set(
    CacheKeys.PRODUCTS_LIST,
    response_data,
    timeout=CacheTimeouts.PRODUCT_DATA,
    category_id=1
)
```

### Invalidación Automática

```python
# Se ejecuta automáticamente al modificar datos
def _invalidate_product_cache(category_id=None):
    cache_manager.delete_pattern(f"{CacheKeys.PRODUCTS_LIST}*")
    cache_manager.delete_pattern(f"{CacheKeys.PRODUCTS_SEARCH}*")
    if category_id:
        cache_manager.delete_pattern(f"{CacheKeys.PRODUCTS_BY_CATEGORY}*")
```

## 🛠️ Administración

### Comandos de Terminal

```bash
# Ver estadísticas
python manage.py cache_admin stats --verbose

# Limpiar todo el cache
python manage.py cache_admin clear

# Limpiar por patrón
python manage.py cache_admin clear-pattern --pattern "products:*"

# Listar claves
python manage.py cache_admin keys --verbose

# Precalentar cache
python manage.py cache_admin warm-up
```

### API Endpoints de Administración

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v2/admin/cache/stats` | GET | Estadísticas completas |
| `/api/v2/admin/cache/clear-pattern` | POST | Limpiar por patrón |
| `/api/v2/admin/cache/clear-all` | POST | Limpiar todo |
| `/api/v2/admin/cache/warm-up` | POST | Precalentar cache |

### Ejemplo de Uso de API

```bash
# Obtener estadísticas
curl -H "Authorization: Bearer <token>" \
     https://api.ejemplo.com/api/v2/admin/cache/stats

# Limpiar productos
curl -X POST \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"pattern": "products:*", "confirm": true}' \
     https://api.ejemplo.com/api/v2/admin/cache/clear-pattern
```

## 📈 Monitoreo

### Headers de Debug

En modo DEBUG, las respuestas incluyen headers informativos:

- `X-Cache-Hits`: Número de hits de cache
- `X-Cache-Misses`: Número de misses
- `X-Cache-Status`: HIT, MISS o MIXED
- `X-Cache-Processing-Time`: Tiempo de procesamiento

### Logs

El sistema registra automáticamente:

- Operaciones de cache (DEBUG level)
- Invalidaciones (INFO level)
- Errores (ERROR level)
- Actividad por request (INFO level)

## 🔍 Métricas y Estadísticas

### Estadísticas Disponibles

```python
stats = cache_manager.get_stats()
# Retorna:
{
    'hits': 150,
    'misses': 25,
    'sets': 50,
    'deletes': 10,
    'total_requests': 175,
    'hit_rate_percent': 85.7
}
```

### Información de Redis

- Versión de Redis
- Memoria utilizada
- Clientes conectados
- Comandos procesados
- Tiempo de actividad

## 🧪 Testing

### Tests Implementados

1. **CacheUtilsTestCase**: Tests unitarios del CacheManager
2. **ProductsCacheTestCase**: Tests de cache en productos
3. **CategoriesCacheTestCase**: Tests de cache en categorías
4. **InventoryCacheTestCase**: Tests de cache en inventario
5. **AnalyticsCacheTestCase**: Tests de cache en analytics
6. **CacheIntegrationTestCase**: Tests de integración

### Ejecutar Tests

```bash
# Todos los tests de cache
python manage.py test api.tests.test_cache

# Tests específicos
python manage.py test api.tests.test_cache.CacheUtilsTestCase

# Con coverage
coverage run --source='.' manage.py test api.tests.test_cache
coverage report
```

## 🚨 Troubleshooting

### Problemas Comunes Resueltos

#### 1. **Error "Connection refused" en Redis**

**Síntoma**: `Error 111 connecting to redis:6379. Connection refused.`

**Causa**: Redis configurado con `bind 127.0.0.1` solo acepta conexiones localhost.

**Solución aplicada**:

```properties
# En redis/redis.conf
bind 0.0.0.0              # En lugar de 127.0.0.1 ::1
protected-mode no         # Permitir conexiones remotas con auth
```

#### 2. **Error de Autenticación Redis**

**Síntoma**: `AUTH called without any password configured for the default user`

**Causa**: Variable de entorno `REDIS_PASSWORD` no se pasa correctamente al comando.

**Solución aplicada**:

```yaml
# En docker-compose.yml
environment:
  - REDIS_PASSWORD=tu-password-redis-seguro
command: 
  - redis-server
  - /usr/local/etc/redis/redis.conf
  - --requirepass
  - tu-password-redis-seguro  # Hardcodeado en lugar de ${REDIS_PASSWORD}
```

#### 3. **Django Extensions Missing**

**Síntoma**: `ModuleNotFoundError: No module named 'django_extensions'`

**Solución aplicada**: Agregado al `requirements.txt`:

```pip
django-extensions==3.2.3
```

### Problemas de Configuración

4. **Cache no funciona**
   - Verificar conexión Redis: `docker logs redis_cache`
   - Verificar configuración en settings.py
   - Verificar variable de entorno `REDIS_PASSWORD`

5. **Datos desactualizados**
   - Verificar invalidación automática
   - Limpiar cache manualmente: `python manage.py cache_admin clear`

6. **Memoria de Redis llena**
   - Ajustar `maxmemory` en `redis.conf`
   - Verificar política de evicción LRU

7. **Performance degradada**
   - Revisar logs de cache
   - Verificar hit rate en estadísticas
   - Ajustar timeouts según uso

### Logs de Diagnóstico

```bash
# Ver logs de Redis
docker logs redis_cache

# Ver logs de la aplicación
docker logs backend_api_compras | grep -i cache

# Logs en tiempo real
docker logs -f backend_api_compras | grep -E "(cache|Cache)"
```

## 📋 Mejores Prácticas

### Desarrollo

1. **Usar cache_manager** en lugar de cache directo
2. **Incluir parámetros** en claves para diferenciación
3. **Invalidar correctamente** tras modificaciones
4. **Configurar timeouts apropiados** según frecuencia de cambio
5. **Testear invalidación** en tests automatizados

### Producción

1. **Monitorear hit rate** regularmente
2. **Ajustar memoria de Redis** según uso
3. **Hacer backup de configuración** Redis
4. **Limpiar cache** antes de deployments críticos
5. **Configurar alertas** para problemas de Redis

### Seguridad

1. **Solo admins** pueden gestionar cache
2. **Patrones validados** para limpieza
3. **Confirmación requerida** para operaciones destructivas
4. **Logs de auditoría** para cambios de cache

## 🔄 Mantenimiento

### Tareas Regulares

1. **Semanalmente**: Revisar estadísticas y hit rate
2. **Mensualmente**: Limpiar claves expiradas manualmente
3. **Trimestralmente**: Revisar y ajustar timeouts
4. **Antes de deployments**: Limpiar cache si hay cambios estructurales

### Automatización

Considera automatizar con cron jobs:

```bash
# Limpiar cache cada domingo a las 2 AM
0 2 * * 0 cd /app && python manage.py cache_admin clear

# Estadísticas diarias
0 1 * * * cd /app && python manage.py cache_admin stats >> /var/log/cache-stats.log
```

## 📚 Referencias

- [Django Cache Framework](https://docs.djangoproject.com/en/stable/topics/cache/)
- [Redis Documentation](https://redis.io/documentation)
- [django-redis](https://github.com/jazzband/django-redis)

---

*Documentación actualizada: Septiembre 2025*  
*Versión del sistema de cache: 1.0*
