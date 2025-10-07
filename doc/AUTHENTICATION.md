# 🔐 Autenticación y Seguridad

Documentación completa del sistema de autenticación JWT y medidas de seguridad implementadas.

## 📋 Tabla de Contenidos

- [Visión General](#visión-general)
- [JWT (JSON Web Tokens)](#jwt-json-web-tokens)
- [Endpoints de Autenticación](#endpoints-de-autenticación)
- [Permisos](#permisos)
- [Seguridad](#seguridad)
- [Buenas Prácticas](#buenas-prácticas)

---

## Visión General

La API utiliza **JWT (JSON Web Tokens)** para autenticación stateless, proporcionando escalabilidad y compatibilidad con aplicaciones móviles y SPAs.

### Stack de Seguridad

- **djangorestframework-simplejwt 5.3.1**: Tokens JWT
- **Django Auth**: Sistema de usuarios y permisos
- **CORS Headers**: Control de acceso cross-origin
- **HTTPS**: Comunicación encriptada (producción)
- **Django Security**: Protección XSS, CSRF, SQL Injection

---

## JWT (JSON Web Tokens)

### ¿Qué es JWT?

JWT es un estándar abierto (RFC 7519) que define un método compacto y autónomo para transmitir información segura entre partes como un objeto JSON.

**Ventajas**:
- ✅ **Stateless**: No requiere sesiones en servidor
- ✅ **Escalable**: Fácil de balancear horizontalmente
- ✅ **Cross-domain**: Compatible con CORS
- ✅ **Móvil-friendly**: Perfecto para apps nativas
- ✅ **Standard**: Ampliamente adoptado

**📚 Referencia**: [JWT.io](https://jwt.io/introduction)

### Estructura de un Token

Un JWT consta de 3 partes separadas por puntos:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20iLCJleHAiOjE3MDk5OTk5OTl9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
|         HEADER                        |                    PAYLOAD                           |              SIGNATURE              |
```

#### 1. Header
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

#### 2. Payload (Claims)
```json
{
  "user_id": 1,
  "email": "user@example.com",
  "exp": 1709999999,
  "iat": 1709996399,
  "jti": "abc123"
}
```

#### 3. Signature
```
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  SECRET_KEY
)
```

### Tipos de Tokens

#### Access Token
- **Propósito**: Autenticar requests API
- **Duración**: 15 minutos (configurable)
- **Uso**: Incluir en header `Authorization: Bearer {access_token}`

#### Refresh Token
- **Propósito**: Obtener nuevos access tokens
- **Duración**: 7 días (configurable)
- **Uso**: Renovar autenticación sin re-login

### Configuración JWT

En `SistemaCompras/settings.py`:

```python
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',
}
```

**📚 Referencia**: [Simple JWT Docs](https://django-rest-framework-simplejwt.readthedocs.io/)

---

## Endpoints de Autenticación

### 1. Registro de Usuario

**Endpoint**: `POST /api/v2/users/register/`

**Request**:
```json
{
  "email": "nuevo@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "first_name": "Juan",
  "last_name": "Pérez"
}
```

**Validaciones**:
- Email único
- Password mínimo 8 caracteres
- Password debe coincidir con password_confirm
- Formato de email válido

**Response** (201 Created):
```json
{
  "id": 42,
  "email": "nuevo@example.com",
  "first_name": "Juan",
  "last_name": "Pérez",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Ejemplo cURL**:
```bash
curl -X POST http://localhost:8000/api/v2/users/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "nuevo@example.com",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!",
    "first_name": "Juan",
    "last_name": "Pérez"
  }'
```

### 2. Obtener Token (Login)

**Endpoint**: `POST /api/v2/token/`

**Request**:
```json
{
  "email": "user@example.com",
  "password": "MyPassword123"
}
```

**Response** (200 OK):
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Ejemplo cURL**:
```bash
curl -X POST http://localhost:8000/api/v2/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "MyPassword123"
  }'
```

**Errores comunes**:
```json
// 401 Unauthorized - Credenciales inválidas
{
  "detail": "No active account found with the given credentials"
}
```

### 3. Refrescar Token

**Endpoint**: `POST /api/v2/token/refresh/`

**Request**:
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response** (200 OK):
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."  // Nuevo refresh token si ROTATE_REFRESH_TOKENS=True
}
```

**Ejemplo cURL**:
```bash
curl -X POST http://localhost:8000/api/v2/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "YOUR_REFRESH_TOKEN_HERE"
  }'
```

### 4. Verificar Token

**Endpoint**: `POST /api/v2/token/verify/`

**Request**:
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response** (200 OK):
```json
{}  // Token válido
```

**Errores**:
```json
// 401 Unauthorized - Token inválido o expirado
{
  "detail": "Token is invalid or expired",
  "code": "token_not_valid"
}
```

### 5. Perfil del Usuario Actual

**Endpoint**: `GET /api/v2/users/me/`

**Headers**:
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

**Response** (200 OK):
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "Juan",
  "last_name": "Pérez",
  "is_active": true,
  "is_staff": false,
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-15T10:30:00Z"
}
```

**Ejemplo cURL**:
```bash
curl -X GET http://localhost:8000/api/v2/users/me/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 6. Actualizar Perfil

**Endpoint**: `PATCH /api/v2/users/me/`

**Request**:
```json
{
  "first_name": "Juan Carlos",
  "last_name": "Pérez González"
}
```

**Response** (200 OK):
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "Juan Carlos",
  "last_name": "Pérez González",
  "is_active": true,
  "updated_at": "2024-01-15T11:00:00Z"
}
```

---

## Permisos

### Permisos Built-in de Django

```python
from rest_framework.permissions import (
    IsAuthenticated,        # Usuario autenticado
    IsAdminUser,           # Usuario es staff
    AllowAny,              # Sin restricciones
    IsAuthenticatedOrReadOnly,  # Autenticado para escribir
)
```

### Permisos Personalizados

En `api/permissions.py`:

#### 1. `IsOwnerOrReadOnly`

Permite edición solo al propietario del objeto.

```python
class IsOwnerOrReadOnly(BasePermission):
    """
    Permite editar solo al propietario del objeto.
    Lectura permitida para todos los autenticados.
    """
    
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:  # GET, HEAD, OPTIONS
            return True
        
        return obj.user == request.user
```

**Uso**:
```python
class PurchaseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
```

#### 2. `IsStaffOrReadOnly`

Permite modificaciones solo a usuarios staff.

```python
class IsStaffOrReadOnly(BasePermission):
    """
    Permite modificaciones solo a usuarios staff.
    Lectura permitida para todos.
    """
    
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        
        return request.user and request.user.is_staff
```

### Aplicación de Permisos

#### A nivel de ViewSet
```python
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]  # Todos los métodos requieren auth
```

#### A nivel de Action
```python
class ReportViewSet(viewsets.GenericViewSet):
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def create_sales_report(self, request):
        # Solo usuarios autenticados pueden crear reportes
        pass
    
    @action(detail=True, methods=['get'], permission_classes=[IsOwnerOrReadOnly])
    def download(self, request, pk=None):
        # Solo el propietario puede descargar su reporte
        pass
```

---

## Seguridad

### Protecciones Implementadas

#### 1. HTTPS (Producción)

```python
# settings.py
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
```

#### 2. CORS (Cross-Origin Resource Sharing)

```python
# settings.py
INSTALLED_APPS = [
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    # ...
]

# Desarrollo
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Frontend React/Vue/Angular
    "http://localhost:8080",
]

# Producción
CORS_ALLOWED_ORIGINS = [
    "https://tudominio.com",
]
```

**📚 Referencia**: [django-cors-headers](https://github.com/adamchainz/django-cors-headers)

#### 3. Rate Limiting

Protección contra fuerza bruta:

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',      # Anónimos: 100 requests/día
        'user': '1000/day',     # Autenticados: 1000 requests/día
        'login': '5/min',       # Login: 5 intentos/minuto
    }
}
```

**Uso específico**:
```python
from rest_framework.throttling import UserRateThrottle

class LoginRateThrottle(UserRateThrottle):
    scope = 'login'

class TokenObtainPairView(TokenObtainPairView):
    throttle_classes = [LoginRateThrottle]
```

#### 4. Password Hashing

Django usa **PBKDF2** por defecto (NIST recomendado):

```python
# settings.py
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',  # Opcional: Requiere argon2-cffi
]
```

**Validaciones**:
```python
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
```

**📚 Referencia**: [Django Password Management](https://docs.djangoproject.com/en/5.1/topics/auth/passwords/)

#### 5. SQL Injection

Django ORM previene automáticamente:

```python
# ✅ SEGURO - ORM parametrizado
products = Product.objects.filter(name=user_input)

# ❌ PELIGROSO - Raw SQL sin sanitizar
products = Product.objects.raw(f"SELECT * FROM products WHERE name = '{user_input}'")

# ✅ SEGURO - Raw SQL con parámetros
products = Product.objects.raw("SELECT * FROM products WHERE name = %s", [user_input])
```

#### 6. XSS (Cross-Site Scripting)

Django escapa automáticamente en templates:

```django
{# ✅ SEGURO - Auto-escaped #}
<p>{{ user_input }}</p>

{# ❌ PELIGROSO - Sin escapar #}
<p>{{ user_input|safe }}</p>
```

En API, JSON es seguro por naturaleza.

#### 7. CSRF Protection

APIs REST son stateless, CSRF no aplica. Usar JWT en su lugar.

```python
# views.py
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

@api_view(['POST'])
@csrf_exempt  # No necesario en DRF, ya está exento
def api_endpoint(request):
    pass
```

---

## Buenas Prácticas

### 1. Gestión de Tokens en Frontend

#### Almacenamiento Seguro

**✅ RECOMENDADO**: HttpOnly Cookies + SameSite
```javascript
// Backend establece cookie HttpOnly
response.set_cookie(
    'access_token', 
    access_token,
    httponly=True,
    secure=True,
    samesite='Strict'
)
```

**⚠️ ALTERNATIVA**: localStorage (menos seguro, vulnerable a XSS)
```javascript
// Solo si no hay alternativa
localStorage.setItem('access_token', token);
```

**❌ EVITAR**: sessionStorage o variables globales

#### Refresh Token Flow

```javascript
// Interceptor Axios para auto-refresh
axios.interceptors.response.use(
  response => response,
  async error => {
    if (error.response.status === 401) {
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post('/api/v2/token/refresh/', {
          refresh: refreshToken
        });
        
        localStorage.setItem('access_token', response.data.access);
        
        // Reintentar request original
        error.config.headers['Authorization'] = `Bearer ${response.data.access}`;
        return axios.request(error.config);
      } catch (refreshError) {
        // Refresh falló, redirigir a login
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
```

### 2. Logout

```python
# views.py
from rest_framework_simplejwt.tokens import RefreshToken

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Invalida el refresh token (blacklist).
    """
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()  # Requiere BLACKLIST_AFTER_ROTATION=True
        
        return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
```

**Frontend**:
```javascript
// Eliminar tokens del almacenamiento
localStorage.removeItem('access_token');
localStorage.removeItem('refresh_token');

// Llamar endpoint de logout
await axios.post('/api/v2/logout/', { refresh: refreshToken });

// Redirigir
window.location.href = '/login';
```

### 3. Validación de Email

```python
# serializers.py
from django.core.validators import EmailValidator

class UserRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        validators=[EmailValidator(message="Email format invalid")]
    )
```

### 4. Secrets Management

**❌ NUNCA hacer commit de**:
- `SECRET_KEY`
- `DATABASE_PASSWORD`
- `REDIS_PASSWORD`
- Tokens API de terceros

**✅ Usar variables de entorno**:
```python
# settings.py
import os

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable not set")
```

**✅ `.env` en `.gitignore`**:
```
# .gitignore
.env
*.env
.env.local
```

### 5. Logging de Seguridad

```python
# settings.py
LOGGING = {
    'version': 1,
    'handlers': {
        'security': {
            'class': 'logging.FileHandler',
            'filename': 'logs/security.log',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['security'],
            'level': 'WARNING',
        },
    },
}
```

---

## Próximos Pasos

Para información complementaria:

- **Arquitectura**: Ver [Architecture](ARCHITECTURE.md)
- **Testing de Autenticación**: Ver [Testing](TESTING.md)
- **Deployment Seguro**: Ver [Installation](INSTALLATION.md#producción)

---

**📚 Volver a**: [README principal](../README.md)
