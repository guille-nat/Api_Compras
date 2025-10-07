# 📥 Guía de Instalación - Sistema de Compras

Esta guía cubre todos los métodos de instalación del Sistema de Compras: Docker (recomendado), instalación manual y configuración para desarrollo.

## 📋 Tabla de Contenidos

- [Prerequisitos](#prerequisitos)
- [Instalación con Docker (Recomendado)](#instalación-con-docker-recomendado)
- [Instalación Manual](#instalación-manual)
- [Configuración](#configuración)
- [Verificación](#verificación)
- [Troubleshooting](#troubleshooting)

---

## Prerequis itos

### Para Docker

- Docker Desktop 20.10+
- Docker Compose 2.0+
- 4GB RAM mínimo
- 10GB espacio en disco
- Git

### Para Instalación Manual

- Python 3.10 o superior
- MySQL 9.0
- Redis 7.0
- pip 21.0+
- virtualenv
- Git

---

## Instalación con Docker (Recomendado)

### 1. Clonar el Repositorio

```bash
git clone https://github.com/guille-nat/Api_Compras.git
cd Api_Compras
```

### 2. Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp API_Compras/.env.example API_Compras/.env

# Editar archivo .env
nano API_Compras/.env  # o usar tu editor preferido
```

**Variables críticas a configurar**:
```env
# Django
SECRET_KEY=tu-secret-key-super-segura
DEBUG=False  # True solo en desarrollo
ALLOWED_HOSTS=localhost,127.0.0.1,tudominio.com

# MySQL
MYSQL_DATABASE=sistema_compras
MYSQL_USER=admin_user
MYSQL_PASSWORD=password-muy-seguro
MYSQL_ROOT_PASSWORD=root-password-muy-seguro

# Redis
REDIS_PASSWORD=redis-password-seguro

# Email (opcional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password

# Signals (dejar en False para producción)
DISABLE_SIGNALS=False
```

**📄 Guía completa**: Ver [Variables de Entorno](ENVIRONMENT.md)

### 3. Construir e Iniciar Servicios

```bash
# Construir imágenes e iniciar servicios
docker-compose up -d --build

# Ver logs en tiempo real
docker-compose logs -f

# Verificar servicios activos
docker ps
```

**Servicios esperados**:
```
CONTAINER ID   IMAGE                    STATUS
xxxxxxxxx      sistemacompras-backend   Up (healthy)
xxxxxxxxx      celery_worker            Up
xxxxxxxxx      celery_beat              Up
xxxxxxxxx      redis:7-alpine           Up (healthy)
xxxxxxxxx      mysql:9.0                Up (healthy)
```

### 4. Aplicar Migraciones

```bash
# Aplicar migraciones de base de datos
docker-compose exec backend python manage.py migrate

# Crear superusuario
docker-compose exec backend python manage.py createsuperuser
```

### 5. Generar Datos de Prueba (Opcional)

```bash
# Deshabilitar signals para evitar emails de prueba
$env:DISABLE_SIGNALS="True"  # PowerShell
# set DISABLE_SIGNALS=True   # CMD
# export DISABLE_SIGNALS=True # Bash

# Generar datos
docker-compose exec backend python manage.py generate_data --products 500 --users 100

# Rehabilitar signals
$env:DISABLE_SIGNALS="False"
```

### 6. Acceder a la Aplicación

| Servicio | URL | Credenciales |
|----------|-----|--------------|
| API Base | http://localhost:8000/api/v2/ | JWT Token |
| Admin Panel | http://localhost:8000/admin/ | Superuser |
| Swagger UI | http://localhost:8000/api/v2/schema/swagger-ui/ | - |
| ReDoc | http://localhost:8000/api/v2/schema/redoc/ | - |
| Cache Stats | http://localhost:8000/api/v2/admin/cache/stats/ | Admin |

---

## Instalación Manual

### 1. Clonar Repositorio

```bash
git clone https://github.com/guille-nat/Api_Compras.git
cd Api_Compras/API_Compras
```

### 2. Crear Entorno Virtual

**Linux/Mac**:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows PowerShell**:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows CMD**:
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

### 3. Instalar Dependencias

```bash
# Actualizar pip
pip install --upgrade pip setuptools wheel

# Instalar requirements
pip install -r requirements.txt
```

**Problemas comunes**:
- `mysqlclient`: Requiere MySQL connector C
- `Pillow`: Requiere libjpeg, zlib
- Ver sección [Troubleshooting](#troubleshooting)

### 4. Configurar MySQL

```sql
-- Crear base de datos
CREATE DATABASE sistema_compras CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Crear usuario
CREATE USER 'admin_user'@'localhost' IDENTIFIED BY 'password-seguro';

-- Otorgar permisos
GRANT ALL PRIVILEGES ON sistema_compras.* TO 'admin_user'@'localhost';
FLUSH PRIVILEGES;
```

### 5. Configurar Redis

**Linux/Mac**:
```bash
# Instalar Redis
brew install redis  # Mac
# sudo apt install redis # Ubuntu

# Iniciar Redis
redis-server

# Configurar password (redis.conf)
requirepass tu-password-seguro
```

**Windows**:
```powershell
# Descargar desde https://redis.io/download
# O usar Docker:
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

### 6. Variables de Entorno

```bash
# Copiar archivo ejemplo
cp .env.example .env

# Editar .env
nano .env
```

**Configuración mínima**:
```env
SECRET_KEY=tu-secret-key-generada
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

MYSQL_DATABASE=sistema_compras
MYSQL_USER=admin_user
MYSQL_PASSWORD=password-seguro
MYSQL_HOST=localhost
MYSQL_PORT=3306

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=tu-password-seguro
```

### 7. Aplicar Migraciones

```bash
# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Recolectar archivos estáticos
python manage.py collectstatic --noinput
```

### 8. Iniciar Servidor de Desarrollo

```bash
# Iniciar Django
python manage.py runserver

# En otra terminal: Iniciar Celery Worker
celery -A SistemaCompras worker -l info

# En otra terminal: Iniciar Celery Beat
celery -A SistemaCompras beat -l info
```

---

## Configuración

### Configuración de Producción

1. **Cambiar DEBUG a False**:
```env
DEBUG=False
```

2. **Configurar ALLOWED_HOSTS**:
```env
ALLOWED_HOSTS=tudominio.com,www.tudominio.com
```

3. **Usar SECRET_KEY segura**:
```bash
# Generar nueva SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

4. **Configurar HTTPS**:
```python
# settings.py
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

5. **Configurar CORS** (si es necesario):
```env
CORS_ALLOWED_ORIGINS=https://tudominio.com,https://app.tudominio.com
```

### Optimizaciones de Performance

1. **Configurar Gunicorn**:
```bash
pip install gunicorn

# Ejecutar
gunicorn SistemaCompras.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

2. **Configurar Nginx** (reverse proxy):
```nginx
server {
    listen 80;
    server_name tudominio.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static/ {
        alias /ruta/al/proyecto/staticfiles/;
    }

    location /media/ {
        alias /ruta/al/proyecto/media/;
    }
}
```

---

## Verificación

### Verificar Instalación Docker

```bash
# 1. Verificar servicios
docker ps

# 2. Verificar logs
docker-compose logs backend | tail -n 50

# 3. Test de conexión MySQL
docker-compose exec backend python manage.py dbshell

# 4. Test de conexión Redis
docker-compose exec backend python -c "from django.core.cache import cache; cache.set('test', 'ok', 10); print(cache.get('test'))"

# 5. Test de API
curl http://localhost:8000/api/v2/

# 6. Test de Celery
docker-compose exec backend celery -A SistemaCompras inspect active
```

### Verificar Instalación Manual

```bash
# 1. Verificar dependencias
pip list

# 2. Verificar conexión MySQL
python manage.py dbshell

# 3. Verificar conexión Redis
python -c "from django.core.cache import cache; cache.set('test', 'ok'); print(cache.get('test'))"

# 4. Verificar migraciones
python manage.py showmigrations

# 5. Ejecutar tests
pytest

# 6. Verificar Celery
celery -A SistemaCompras inspect active
```

---

## Troubleshooting

### Error: mysqlclient no compila

**Problema**: No se puede instalar `mysqlclient`

**Solución Linux**:
```bash
sudo apt-get install python3-dev default-libmysqlclient-dev build-essential
pip install mysqlclient
```

**Solución Mac**:
```bash
brew install mysql-client
export PKG_CONFIG_PATH="/usr/local/opt/mysql-client/lib/pkgconfig"
pip install mysqlclient
```

**Solución Windows**:
```powershell
# Descargar wheel desde:
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#mysqlclient
pip install mysqlclient‑2.2.7‑cp310‑cp310‑win_amd64.whl
```

### Error: Redis no conecta

**Verificar Redis**:
```bash
# Verificar que Redis está corriendo
redis-cli ping
# Debe responder: PONG

# Con password
redis-cli -a tu-password ping
```

**Problema común**: Password no coincide
```env
# Verificar en .env
REDIS_PASSWORD=password-correcto
```

### Error: Permission Denied en Docker

**Linux**:
```bash
# Agregar usuario al grupo docker
sudo usermod -aG docker $USER

# Reiniciar sesión
newgrp docker
```

### Error: Puerto 8000 ya en uso

```bash
# Encontrar proceso usando el puerto
# Linux/Mac
lsof -i :8000

# Windows
netstat -ano | findstr :8000

# Matar proceso
kill -9 PID  # Linux/Mac
taskkill /PID PID /F  # Windows
```

### Error: Migraciones fallan

```bash
# Resetear migraciones (⚠️ solo en desarrollo)
python manage.py migrate --fake

# O eliminar base de datos y recrear
docker-compose down -v
docker-compose up -d
docker-compose exec backend python manage.py migrate
```

### Logs y Debug

```bash
# Ver logs de Django
docker-compose logs -f backend

# Ver logs de Celery Worker
docker-compose logs -f celery_worker

# Ver logs de MySQL
docker-compose logs -f db

# Ver logs de Redis
docker-compose logs -f redis

# Entrar al contenedor para debug
docker-compose exec backend bash
```

---

## Próximos Pasos

Después de completar la instalación:

1. ✅ Leer [Arquitectura del Sistema](ARCHITECTURE.md)
2. ✅ Revisar [Documentación de API](API_STANDARDS.md)
3. ✅ Configurar [Sistema de Cache](CACHE.md)
4. ✅ Aprender sobre [Reportes Asíncronos](ANALYTICS.md)
5. ✅ Configurar [Autenticación JWT](AUTHENTICATION.md)

---

**📚 Documentación completa**: Ver [README principal](../README.md)
