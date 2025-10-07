# 🔐 Variables de Entorno - API Sistema de Compras

## 📋 Descripción

Este documento detalla todas las variables de entorno necesarias para la correcta configuración y funcionamiento de la API Sistema de Compras. Las variables están organizadas por categorías y incluyen ejemplos de valores seguros.

## 📁 Ubicación del Archivo

Crea el archivo `.env` en la ruta: `API_Compras/.env`

## 🔧 Variables de Entorno Requeridas

### 1. Django Core Configuration

```env
# ===========================
# Django Configuration
# ===========================

# Clave secreta de Django (CRÍTICO: Cambiar en producción)
SECRET_KEY='django-insecure-4s(f1y7kc7p85^zzh*kkxmwww3erv0%hx__bz-aav%hu3!frzy'

# Modo debug (True para desarrollo, False para producción)
DEBUG=True

# Hosts permitidos (* para desarrollo, dominio específico para producción)
ALLOWED_HOSTS=*
```

**Descripción**:
- `SECRET_KEY`: Clave criptográfica usada por Django para firmar cookies, tokens, etc.
- `DEBUG`: Controla el modo de depuración (logs detallados, páginas de error)
- `ALLOWED_HOSTS`: Lista de hosts/dominios permitidos para servir la aplicación

### 2. JWT Authentication

```env
# ===========================  
# JWT Authentication
# ===========================

# Clave secreta para firmar tokens JWT (CRÍTICO: Cambiar en producción)
SECRET_KEY_JWT=')KvE%`R>5+d0<J?tUktRW[I@L8xz_I@OB:T#V2we*W1r@cuBB:-sQB_7{9hF-:&G'
```

**Descripción**:
- `SECRET_KEY_JWT`: Clave específica para firmado de tokens JWT (autenticación API)

### 3. MySQL Database Configuration

```env
# ===========================
# MySQL Database
# ===========================

# Nombre de la base de datos
MYSQL_DATABASE=sistema_compras

# Usuario de MySQL para la aplicación
MYSQL_USER=guille-natali-admin

# Contraseña del usuario MySQL (CRÍTICO: Usar contraseña fuerte)
MYSQL_PASSWORD='IF3ase~>(+R/kzqF9B__Q-]23qfMNpELt!m4Sr#KN_C&->VU`IYJ{X995jX$XXeN'

# Contraseña del usuario root de MySQL
MYSQL_ROOT_PASSWORD='IF3ase~>(+R/kzqF9B__Q-]23qfMNpELt!m4Sr#KN_C&->VU`IYJ{X995jX$XXeN'

# Host del servidor MySQL (en Docker: 'db', en localhost: '127.0.0.1')
MYSQL_HOST=db

# Puerto de MySQL (por defecto: 3306)
MYSQL_PORT=3306
```

**Descripción**:
- `MYSQL_DATABASE`: Nombre de la base de datos que usará la aplicación
- `MYSQL_USER`: Usuario con permisos sobre la base de datos específica
- `MYSQL_PASSWORD`: Contraseña del usuario de aplicación
- `MYSQL_ROOT_PASSWORD`: Contraseña del superusuario MySQL
- `MYSQL_HOST`: Dirección del servidor MySQL
- `MYSQL_PORT`: Puerto de conexión MySQL

### 4. Redis Cache Configuration

```env
# ===========================
# Redis Cache
# ===========================

# Contraseña de Redis (CRÍTICO: Usar contraseña fuerte)
REDIS_PASSWORD=S2yU-un9jDA-IU-8tpKEg-b-EGej5cUI8-8Jju-k-U9-3MU-b-zzUUg-Redis2025

# Host del servidor Redis (en Docker: 'redis', en localhost: '127.0.0.1')
REDIS_HOST=redis

# Puerto de Redis (por defecto: 6379)
REDIS_PORT=6379
```

**Descripción**:
- `REDIS_PASSWORD`: Contraseña para autenticación en Redis
- `REDIS_HOST`: Dirección del servidor Redis
- `REDIS_PORT`: Puerto de conexión Redis

### 5. Email Configuration (SMTP)

```env
# ===========================
# Email Configuration (Gmail)
# ===========================

# Servidor SMTP (Gmail por defecto)
EMAIL_HOST=smtp.gmail.com

# Puerto SMTP (587 para TLS, 465 para SSL)
EMAIL_PORT=587

# Usar TLS (True recomendado para Gmail)
EMAIL_USE_TLS=True

# Cuenta de correo electrónico
EMAIL_HOST_USER=gutierrezfalopaalberto@gmail.com

# Contraseña de aplicación de Gmail (NO la contraseña de la cuenta)
EMAIL_HOST_PASSWORD=ujak wmtg avbr lxra
```

**Descripción**:
- `EMAIL_HOST`: Servidor SMTP del proveedor de correo
- `EMAIL_PORT`: Puerto del servidor SMTP
- `EMAIL_USE_TLS`: Habilitar cifrado TLS
- `EMAIL_HOST_USER`: Dirección de correo para envío
- `EMAIL_HOST_PASSWORD`: Contraseña específica para aplicaciones (no la del correo)

**⚠️ Nota Gmail**: Usar "Contraseñas de aplicación" no la contraseña de la cuenta.

### 6. Auto-superuser (Desarrollo)

```env
# ===========================
# Auto-superuser (Desarrollo)
# ===========================

# Crear superusuario automáticamente (True para desarrollo)
CREATE_SUPERUSER=true

# Nombre de usuario del superusuario
DJANGO_SUPERUSER_USERNAME=admin

# Email del superusuario
DJANGO_SUPERUSER_EMAIL=admin@example.com

# Contraseña del superusuario (CAMBIAR en producción)
DJANGO_SUPERUSER_PASSWORD=admin
```

**Descripción**:
- `CREATE_SUPERUSER`: Crear automáticamente un superusuario al iniciar
- `DJANGO_SUPERUSER_USERNAME`: Nombre de usuario del administrador
- `DJANGO_SUPERUSER_EMAIL`: Email del administrador
- `DJANGO_SUPERUSER_PASSWORD`: Contraseña del administrador

### 7. Testing Configuration

```env
# ===========================
# Testing Configuration
# ===========================

# Usar SQLite para tests (0 = usar MySQL, 1 = usar SQLite)
USE_SQLITE_FOR_TESTS=0
```

**Descripción**:
- `USE_SQLITE_FOR_TESTS`: Configurar base de datos para testing

## 🏭 Configuración de Producción

Para **producción**, modifica estas variables críticas:

```env
# ===========================
# PRODUCCIÓN - VALORES CRÍTICOS
# ===========================

# Django (CRÍTICO)
DEBUG=False
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com,api.tu-dominio.com
SECRET_KEY='GENERAR-NUEVA-CLAVE-SECRETA-MUY-FUERTE-Y-ALEATORIA'

# JWT (CRÍTICO)
SECRET_KEY_JWT='GENERAR-NUEVA-CLAVE-JWT-MUY-FUERTE-Y-ALEATORIA'

# Base de datos (CRÍTICO)
MYSQL_HOST=tu-servidor-mysql-produccion.com
MYSQL_USER=usuario_produccion
MYSQL_PASSWORD='PASSWORD-SUPER-SEGURO-PRODUCCION-MYSQL'
MYSQL_ROOT_PASSWORD='ROOT-PASSWORD-SUPER-SEGURO-PRODUCCION'

# Redis (CRÍTICO)
REDIS_HOST=tu-servidor-redis-produccion.com
REDIS_PASSWORD='PASSWORD-REDIS-SUPER-SEGURO-PRODUCCION'

# Email producción
EMAIL_HOST_USER=notificaciones@tu-empresa.com
EMAIL_HOST_PASSWORD=password-aplicacion-produccion

# Superuser (CRÍTICO)
CREATE_SUPERUSER=false  # No crear automáticamente
DJANGO_SUPERUSER_PASSWORD=PASSWORD-ADMIN-SUPER-SEGURO
```

## 🔐 Generación de Claves Seguras

### Script Python para generar claves

```python
#!/usr/bin/env python3
import secrets
import string

def generate_django_secret_key():
    """Genera una SECRET_KEY segura para Django"""
    chars = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
    return ''.join(secrets.choice(chars) for _ in range(50))

def generate_jwt_secret_key():
    """Genera una clave JWT segura"""
    return secrets.token_urlsafe(64)

def generate_database_password():
    """Genera una contraseña segura para base de datos"""
    chars = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(secrets.choice(chars) for _ in range(32))

def generate_redis_password():
    """Genera una contraseña segura para Redis"""
    chars = string.ascii_letters + string.digits + '-_'
    return ''.join(secrets.choice(chars) for _ in range(40))

# Generar todas las claves
print("=== CLAVES SEGURAS GENERADAS ===")
print(f"SECRET_KEY='{generate_django_secret_key()}'")
print(f"SECRET_KEY_JWT='{generate_jwt_secret_key()}'")
print(f"MYSQL_PASSWORD='{generate_database_password()}'")
print(f"MYSQL_ROOT_PASSWORD='{generate_database_password()}'")
print(f"REDIS_PASSWORD={generate_redis_password()}")
print("===================================")
```

### Comando rápido

```bash
# Generar SECRET_KEY
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(50))"

# Generar contraseña de BD
python -c "import secrets, string; chars=string.ascii_letters+string.digits+'!@#$%^&*'; print(''.join(secrets.choice(chars) for _ in range(32)))"
```

## 🐳 Variables en Docker Compose

El archivo `docker-compose.yml` lee automáticamente el archivo `.env` ubicado en `API_Compras/.env`.

### Configuración actual

```yaml
services:
  db:
    env_file:
      - ./API_Compras/.env
  
  backend:
    env_file:
      - ./API_Compras/.env
  
  redis:
    env_file:
      - ./API_Compras/.env
    environment:
      - REDIS_PASSWORD=${REDIS_PASSWORD}
```

## ✅ Validación de Variables

### Script de validación

```python
#!/usr/bin/env python3
import os
from pathlib import Path

def validate_env_file():
    """Valida que todas las variables necesarias estén configuradas"""
    env_file = Path("API_Compras/.env")
    
    if not env_file.exists():
        print("❌ Archivo .env no encontrado en API_Compras/.env")
        return False
    
    required_vars = [
        'SECRET_KEY', 'DEBUG', 'ALLOWED_HOSTS',
        'SECRET_KEY_JWT',
        'MYSQL_DATABASE', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_HOST',
        'REDIS_PASSWORD', 'REDIS_HOST', 'REDIS_PORT',
        'EMAIL_HOST', 'EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD'
    ]
    
    missing_vars = []
    
    with open(env_file, 'r') as f:
        content = f.read()
        for var in required_vars:
            if f"{var}=" not in content:
                missing_vars.append(var)
    
    if missing_vars:
        print("❌ Variables faltantes:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    
    print("✅ Todas las variables requeridas están presentes")
    return True

if __name__ == "__main__":
    validate_env_file()
```

## 🚨 Seguridad y Mejores Prácticas

### ✅ Hacer

1. **Cambiar todas las claves** en producción
2. **Usar contraseñas fuertes** (mínimo 32 caracteres)
3. **No commitear** el archivo `.env` al repositorio
4. **Usar HTTPS** en producción (`DEBUG=False`)
5. **Limitar hosts** con dominios específicos
6. **Rotar claves** periódicamente

### ❌ No hacer

1. **No usar valores por defecto** en producción
2. **No commitear secretos** al código
3. **No usar DEBUG=True** en producción
4. **No usar contraseñas simples**
5. **No exponer variables** en logs
6. **No usar la misma clave** para todo

## 📝 Archivo .env.example

Crea un archivo `.env.example` para el repositorio:

```env
# Copiar a .env y completar con valores reales

# Django
SECRET_KEY='cambiar-por-clave-segura'
DEBUG=True
ALLOWED_HOSTS=*

# JWT
SECRET_KEY_JWT='cambiar-por-clave-jwt-segura'

# MySQL
MYSQL_DATABASE=sistema_compras
MYSQL_USER=tu-usuario
MYSQL_PASSWORD='tu-password-seguro'
MYSQL_ROOT_PASSWORD='tu-root-password-seguro'
MYSQL_HOST=db
MYSQL_PORT=3306

# Redis
REDIS_PASSWORD=tu-password-redis-seguro
REDIS_HOST=redis
REDIS_PORT=6379

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password

# Auto-superuser
CREATE_SUPERUSER=true
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com  
DJANGO_SUPERUSER_PASSWORD=cambiar-password

# Testing
USE_SQLITE_FOR_TESTS=0
```

---

**Última actualización**: Septiembre 2025
**Versión**: 1.0
**Estado**: ✅ Funcional con correcciones aplicadas