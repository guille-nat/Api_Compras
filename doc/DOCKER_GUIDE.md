# 🐳 Docker Setup y Troubleshooting - API Sistema de Compras

## 📋 Descripción

Guía completa para configurar, ejecutar y solucionar problemas con Docker en el proyecto API Sistema de Compras. Incluye comandos validados y procedimientos de troubleshooting actualizados.

## 🚀 Setup Completo con Docker

### Pre-requisitos

- Docker Desktop instalado y ejecutándose
- Docker Compose v2.0+
- Git (para clonar el repositorio)
- 4GB RAM mínimo disponible
- 10GB espacio en disco

### Instalación Paso a Paso

```bash
# 1. Clonar el repositorio
git clone https://github.com/guille-nat/Api_Compras.git
cd Api_Compras

# 2. Crear archivo de variables de entorno
cp API_Compras/.env.example API_Compras/.env
# Editar API_Compras/.env con tus configuraciones

# 3. Construir e iniciar todos los servicios
docker-compose up -d --build

# 4. Verificar que todos los servicios estén funcionando
docker ps

# 5. Ver logs para confirmar que todo está OK
docker logs backend_api_compras
docker logs redis_cache
docker logs db_api_compras
```

### Verificación de Servicios

```bash
# Estado de todos los contenedores
docker ps

# Resultado esperado:
# CONTAINER ID   IMAGE                    STATUS
# xxxxxxxxx      sistemacompras-backend   Up X minutes (healthy)
# xxxxxxxxx      redis:7-alpine           Up X minutes (healthy)  
# xxxxxxxxx      mysql:9.0                Up X minutes (healthy)
```

## 🔍 Comandos de Diagnóstico

### 1. Verificar Estado General

```bash
# Estado de contenedores
docker ps -a

# Uso de recursos
docker stats

# Información de red
docker network ls
docker network inspect sistemacompras_api_compras_network
```

### 2. Logs Detallados

```bash
# Ver logs de todos los servicios
docker-compose logs

# Logs específicos por servicio
docker logs backend_api_compras
docker logs redis_cache  
docker logs db_api_compras

# Logs en tiempo real
docker logs -f backend_api_compras

# Últimas 50 líneas
docker logs --tail 50 backend_api_compras
```

### 3. Inspección de Servicios

```bash
# Información detallada de contenedores
docker inspect backend_api_compras
docker inspect redis_cache
docker inspect db_api_compras

# Variables de entorno
docker exec backend_api_compras env
docker exec redis_cache env | grep REDIS
docker exec db_api_compras env | grep MYSQL
```

## 🧪 Comandos de Testing

### Conectividad entre Servicios

```bash
# Test de conectividad MySQL desde backend
docker exec backend_api_compras python -c "
import MySQLdb
try:
    conn = MySQLdb.connect(host='db', user='guille-natali-admin', passwd='tu-password', db='sistema_compras')
    print('✅ MySQL conectado')
    conn.close()
except Exception as e:
    print(f'❌ MySQL error: {e}')
"

# Test de conectividad Redis desde backend  
docker exec backend_api_compras python -c "
import redis
try:
    r = redis.Redis(host='redis', port=6379, password='tu-password-redis')
    print('Redis ping:', r.ping())
    print('✅ Redis conectado')
except Exception as e:
    print(f'❌ Redis error: {e}')
"

# Test de Django
docker exec backend_api_compras python manage.py check

# Test de migraciones
docker exec backend_api_compras python manage.py showmigrations
```

### Health Checks Manuales

```bash
# Health check Redis
docker exec redis_cache redis-cli -a tu-password-redis ping

# Health check MySQL
docker exec db_api_compras mysqladmin ping -h localhost

# Health check Django
curl -f http://localhost:8000/api/v2/ || echo "Django no responde"
```

## 🔧 Comandos de Mantenimiento

### Gestión de Contenedores

```bash
# Reiniciar servicios específicos
docker-compose restart backend
docker-compose restart redis
docker-compose restart db

# Reiniciar todo
docker-compose restart

# Reconstruir e iniciar
docker-compose up -d --build

# Parar todos los servicios
docker-compose down

# Parar y eliminar volúmenes (⚠️ PELIGROSO: Borra datos)
docker-compose down -v
```

### Gestión de Datos

```bash
# Backup de base de datos
docker exec db_api_compras mysqldump -u root -p'tu-root-password' sistema_compras > backup.sql

# Restaurar base de datos
docker exec -i db_api_compras mysql -u root -p'tu-root-password' sistema_compras < backup.sql

# Backup de datos Redis
docker exec redis_cache redis-cli -a tu-password-redis --rdb /data/backup.rdb

# Ver volúmenes
docker volume ls
docker volume inspect sistemacompras_db_api_compras
docker volume inspect sistemacompras_redis_data
```

### Limpieza del Sistema

```bash
# Limpiar contenedores parados
docker container prune

# Limpiar imágenes no utilizadas
docker image prune

# Limpiar volúmenes no utilizados
docker volume prune

# Limpiar redes no utilizadas
docker network prune

# Limpieza completa del sistema (⚠️ CUIDADO)
docker system prune -a
```

## 🚨 Troubleshooting Específico

### Problema 1: Redis Connection Refused

**Síntoma**:
```
Error 111 connecting to redis:6379. Connection refused.
```

**Diagnóstico**:
```bash
# Verificar estado de Redis
docker ps | grep redis
docker logs redis_cache

# Verificar configuración de red
docker exec backend_api_compras ping redis
```

**Solución**:
```bash
# 1. Verificar archivo redis.conf
cat redis/redis.conf | grep bind
# Debe mostrar: bind 0.0.0.0

# 2. Reiniciar Redis
docker-compose restart redis

# 3. Verificar variables de entorno
docker exec redis_cache env | grep REDIS_PASSWORD
```

### Problema 2: MySQL Connection Error

**Síntoma**:
```
MySQLdb._exceptions.OperationalError: (2003, "Can't connect to MySQL server")
```

**Diagnóstico**:
```bash
# Estado de MySQL
docker logs db_api_compras

# Test de conexión
docker exec db_api_compras mysql -u root -p'tu-root-password' -e "SHOW DATABASES;"
```

**Solución**:
```bash
# 1. Verificar variables de entorno
docker exec backend_api_compras env | grep MYSQL

# 2. Verificar health check
docker exec db_api_compras mysqladmin ping -h localhost

# 3. Recrear contenedor si es necesario
docker-compose down db
docker-compose up -d db
```

### Problema 3: Backend No Inicia

**Síntoma**:
```
Container restarting constantly
```

**Diagnóstico**:
```bash
# Ver logs detallados
docker logs backend_api_compras

# Ver código de salida
docker ps -a | grep backend
```

**Soluciones comunes**:
```bash
# 1. Problema de dependencias - reconstruir
docker-compose build --no-cache backend
docker-compose up -d backend

# 2. Problema de migraciones
docker exec backend_api_compras python manage.py migrate

# 3. Problema de permisos
docker exec backend_api_compras chmod +x /entrypoint.sh
```

### Problema 4: Puerto Ocupado

**Síntoma**:
```
Bind for 0.0.0.0:8000 failed: port is already allocated
```

**Solución**:
```bash
# Verificar qué usa el puerto
netstat -tulpn | grep :8000
# o en Windows:
netstat -ano | findstr :8000

# Cambiar puerto en docker-compose.yml
# ports:
#   - "8001:8000"  # Puerto 8001 en lugar de 8000

# O matar proceso que usa el puerto
# kill -9 <PID>
```

### Problema 5: Volúmenes Corruptos

**Síntoma**:
```
Database tables missing or corrupted
```

**Solución** (⚠️ PELIGROSO - Borra datos):
```bash
# 1. Backup si es posible
docker exec db_api_compras mysqldump -u root -p'password' sistema_compras > backup.sql

# 2. Eliminar volúmenes
docker-compose down -v

# 3. Recrear desde cero
docker-compose up -d --build

# 4. Restaurar backup si existe
docker exec -i db_api_compras mysql -u root -p'password' sistema_compras < backup.sql
```

## 📊 Monitoreo y Performance

### Métricas de Contenedores

```bash
# Uso de recursos en tiempo real
docker stats

# Información de memoria/CPU por contenedor
docker exec backend_api_compras free -h
docker exec backend_api_compras top -bn1

# Espacio en disco
docker system df
```

### Logs Centralizados

```bash
# Crear archivo de logging centralizado
docker-compose logs > logs_$(date +%Y%m%d_%H%M%S).txt

# Ver logs por timestamp
docker-compose logs --since="1h"
docker-compose logs --until="2023-09-27T10:00:00"
```

## 🔄 Procedimientos de Deployment

### Desarrollo

```bash
# Setup inicial
git pull origin main
cp API_Compras/.env.example API_Compras/.env
# Editar .env con valores de desarrollo
docker-compose up -d --build
```

### Staging

```bash
# Update a nueva versión
git pull origin staging
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Verificar deployment
docker ps
curl -f http://localhost:8000/api/v2/
```

### Producción

```bash
# Pre-deployment checks
docker-compose config  # Verificar sintaxis
docker images  # Verificar imágenes disponibles

# Deployment con backup
./scripts/backup.sh  # Script custom de backup
docker-compose down
docker-compose pull  # Si usas imágenes pre-construidas
docker-compose up -d --build

# Post-deployment verification
docker ps
curl -f https://api.tudominio.com/api/v2/
./scripts/health_check.sh
```

## 📝 Scripts Útiles

### Health Check Script

```bash
#!/bin/bash
# health_check.sh

echo "🔍 Verificando estado de servicios..."

# Backend
if curl -f http://localhost:8000/api/v2/ > /dev/null 2>&1; then
    echo "✅ Backend: OK"
else
    echo "❌ Backend: FAIL"
fi

# Redis
if docker exec redis_cache redis-cli -a $REDIS_PASSWORD ping > /dev/null 2>&1; then
    echo "✅ Redis: OK"
else
    echo "❌ Redis: FAIL"
fi

# MySQL
if docker exec db_api_compras mysqladmin ping -h localhost > /dev/null 2>&1; then
    echo "✅ MySQL: OK"
else
    echo "❌ MySQL: FAIL"
fi
```

### Backup Script

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

echo "📦 Creando backup en $BACKUP_DIR..."

# Backup MySQL
docker exec db_api_compras mysqldump -u root -p'$MYSQL_ROOT_PASSWORD' sistema_compras > $BACKUP_DIR/mysql_backup.sql

# Backup Redis
docker exec redis_cache redis-cli -a $REDIS_PASSWORD --rdb $BACKUP_DIR/redis_backup.rdb

# Backup archivos de configuración
cp -r API_Compras/.env $BACKUP_DIR/
cp docker-compose.yml $BACKUP_DIR/
cp -r redis/ $BACKUP_DIR/

echo "✅ Backup completado: $BACKUP_DIR"
```

## 🎯 Mejores Prácticas

### Desarrollo

1. **Usar nombres consistentes** para contenedores
2. **Configurar health checks** para todos los servicios
3. **Separar secretos** del código fuente
4. **Monitorear logs** regularmente
5. **Hacer backups** antes de cambios importantes

### Producción

1. **Usar imágenes específicas** (no `latest`)
2. **Configurar límites de recursos**
3. **Implementar monitoring** externo
4. **Automatizar backups**
5. **Configurar alertas** para fallos

### Seguridad

1. **No exponer puertos** innecesarios
2. **Usar contraseñas fuertes**
3. **Actualizar imágenes** regularmente
4. **Limitar acceso** a contenedores
5. **Rotar credenciales** periódicamente

---

**Última actualización**: Septiembre 2025  
**Estado**: ✅ Validado y funcional  
**Versión Docker**: 24.x compatible