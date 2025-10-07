import socket
from pathlib import Path
from dotenv import load_dotenv
import os
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-change-me")

DEBUG = os.getenv("DEBUG", "False") == "True"  # Cambiar en producción a False

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_yasg',
    'drf_spectacular',
    'django_celery_beat',
    'django_celery_results',
    'api',  # app principal (incluye notificaciones)
    'api.products',  # app para productos
    'api.purchases',  # app para compras
    'api.payments',  # app para pagos
    'api.users',  # app para usuarios
    'api.categories',  # app  para las categorías
    'api.storage_location',  # app para los depósitos
    'api.inventories',  # app para los inventarios
    'api.promotions',  # app para promociones
    'api.analytics',  # app para analíticas
]
# Apunta a la app 'users' y al modelo 'CustomUser'
AUTH_USER_MODEL = 'users.CustomUser'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'api.middleware.permission_middleware.PermissionErrorMiddleware',
    'api.middleware.not_found_middleware.NotFoundErrorMiddleware',
    # Middleware de seguridad para manejo de errores
    'api.middleware.secure_error_middleware.SecureErrorMiddleware',
    'api.middleware.secure_error_middleware.SecureDebugMiddleware',
]

ROOT_URLCONF = 'SistemaCompras.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'SistemaCompras.wsgi.application'

DATABASES = {
    'default': {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQL_DATABASE"),
        "USER": os.getenv("MYSQL_USER"),
        "PASSWORD": os.getenv("MYSQL_PASSWORD"),
        'HOST': os.getenv("MYSQL_HOST"),
        'PORT': os.getenv("MYSQL_PORT"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "sql_mode": "STRICT_TRANS_TABLES",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

if os.getenv("USE_SQLITE_FOR_TESTS") == "1":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

# Agrupar migraciones en una sola carpeta
MIGRATION_MODULES = {
    'api': 'migrations.api',
    'users': 'migrations.users',
    'products': 'migrations.products',
    'purchases': 'migrations.purchases',
    'payments': 'migrations.payments',
    'categories': 'migrations.categories',
    'storage_location': 'migrations.storage_location',
    'inventories': 'migrations.inventories',
    'promotions': 'migrations.promotions',
    'analytics': 'migrations.analytics',
}

CORS_ALLOWED_ORIGINS = []
CORS_ALLOW_METHODS = (
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
)
CORS_ALLOW_HEADERS = (
    "accept",
    "authorization",
    "content-type",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
)


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

REST_FRAMEWORK = {
    # Authentication
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),

    # Permissions
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),

    # Parsers
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],

    # Schema
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',

    # Pagination
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,

    # Renderers
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],

    # Throttling
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '10000/day',
        'anon': '5000/day',
    },
}


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=40),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": False,

    "ALGORITHM": "HS256",
    "SIGNING_KEY": os.getenv("SECRET_KEY_JWT", SECRET_KEY),
}

LANGUAGE_CODE = 'es-ar'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = "/static/"
# Carpeta donde collectstatic junta todo para servir en prod
STATIC_ROOT = BASE_DIR / "staticfiles"

# (Opcional) si tenés una carpeta de fuentes estáticas dentro del repo:
# borra esta línea si no existe BASE_DIR/static
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": MEDIA_ROOT,
            "base_url": MEDIA_URL,
        },
    },
    "staticfiles": {
        # Para producción es mejor ManifestStaticFilesStorage (hash en nombres)
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
        # Si preferís sin manifest en local, podés usar:
        # "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

# Deshabilitar signals durante generación de datos de prueba o tests
# Para deshabilitar: export DISABLE_SIGNALS=True (Linux/Mac) o set DISABLE_SIGNALS=True (Windows)
DISABLE_SIGNALS = os.getenv("DISABLE_SIGNALS", "False") == "True"

# Configuración robusta de logging


def get_logging_config():
    """
    Retorna configuración de logging robusta que maneja diferentes entornos.
    """
    logs_dir = os.path.join(BASE_DIR, 'logs')

    # Intentar crear directorio de logs
    try:
        os.makedirs(logs_dir, exist_ok=True)
        file_logging_available = True
    except (OSError, PermissionError):
        file_logging_available = False

    # Configuración base
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'simple': {
                'format': '[{levelname}] {asctime} {name}: {message}',
                'style': '{',
            },
            'detailed': {
                'format': '[{levelname}] {asctime} {name} ({pathname}:{lineno}): {message}',
                'style': '{',
            },
            'security': {
                'format': '[SECURITY] {asctime} {name}: {message}',
                'style': '{',
            },
        },
        'filters': {
            'require_debug_false': {
                '()': 'django.utils.log.RequireDebugFalse',
            },
            'require_debug_true': {
                '()': 'django.utils.log.RequireDebugTrue',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
            },
            'console_debug': {
                'class': 'logging.StreamHandler',
                'formatter': 'detailed',
                'filters': ['require_debug_true'],
            },
            'security_log': {
                'class': 'logging.StreamHandler',
                'formatter': 'security',
                'level': 'WARNING',
            },
            'error_console': {
                'class': 'logging.StreamHandler',
                'formatter': 'security',
                'level': 'ERROR',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': True,
            },
            'api.middleware.secure_error_middleware': {
                'handlers': ['security_log'],
                'level': 'WARNING',
                'propagate': False,
            },
            'api.analytics.services': {
                'handlers': ['console_debug'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'api.analytics.views': {
                'handlers': ['console_debug'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'api': {
                'handlers': ['console_debug'],
                'level': 'DEBUG',
                'propagate': False,
            },
        },
    }

    # Agregar logging a archivo solo si está disponible
    if file_logging_available:
        try:
            config['handlers']['error_file'] = {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(logs_dir, 'errors.log'),
                'maxBytes': 1024*1024*5,  # 5MB
                'backupCount': 5,
                'formatter': 'detailed',
                'level': 'ERROR',
            }
            # Agregar error_file a los handlers de seguridad
            config['loggers']['api.middleware.secure_error_middleware']['handlers'].append(
                'error_file')
            config['loggers']['api.analytics.services']['handlers'].append(
                'error_file')
            config['loggers']['api.analytics.views']['handlers'].append(
                'error_file')
        except Exception:
            # Si falla la configuración de archivos, continuar sin ellos
            pass

    return config


LOGGING = get_logging_config()

SPECTACULAR_SETTINGS = {
    'TITLE': '🛒 API Sistema de Compras',
    'DESCRIPTION': '''
📄 Descripción
    API diseñada para la gestión completa de compras, pagos, cuotas, inventario y usuarios. 
    Este proyecto incluye validaciones robustas y reglas de negocio para asegurar un manejo 
    eficiente y seguro de las operaciones comerciales.

🔒 Autenticación
    Esta API utiliza **JWT (JSON Web Tokens)** con esquema Bearer para la autenticación.
    
🚀 Pasos para autenticarse:
    1. **Obtener Token**: POST a `/api/v2/token/` con credenciales
    2. **Usar Token**: Incluir `Authorization: Bearer <token>` en headers
    3. **Renovar Token**: POST a `/api/v2/token/refresh/` con refresh token

🏗️ Arquitectura
    - **Framework**: Django + Django REST Framework
    - **Base de datos**: MySQL 9
    - **Autenticación**: JWT con Simple JWT
    - **Documentación**: O penAPI 3.0 + Swagger UI

📋 Reglas de Negocio Principales
    
🛒 Compras:
    - Validación automática de stock antes de procesar compras
    - Cálculo dinámico de cuotas con incrementos por financiamiento
    - Aplicación de descuentos y promociones

💰 Pagos y Cuotas:
    - Descuento del 5% por pronto pago
    - Recargo del 8% por pago tardío
    - Incremento del 15% en cuotas mayores a 6

📦 Inventario:
    - Gestión de ubicaciones de almacenamiento
    - Control de lotes y fechas de vencimiento
    - Movimientos de entrada, salida y ajustes

🔗 Enlaces Útiles
    - **Documentación Completa**: [README](https://github.com/guille-nat/Api_Compras)
    - **Soporte**: guillermonatali22@gmail.com
    - **Portfolio**: [nataliullacoder.com](https://nataliullacoder.com/)
    ''',
    'VERSION': '2.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {
        'name': 'Guillermo Natali Ulla',
        'url': 'https://nataliullacoder.com/',
        'email': 'guillermonatali22@gmail.com'
    },
    'LICENSE': {
        'name': 'MIT License',
        'url': 'https://opensource.org/licenses/MIT'
    },
    'EXTERNAL_DOCS': {
        'description': 'Documentación completa del proyecto',
        'url': 'https://github.com/guille-nat/Api_Compras'
    },
    'SERVERS': [
        {
            'url': 'http://localhost:8000',
            'description': 'Servidor de desarrollo'
        },
    ],
    # Activate preprocessing/postprocessing hooks so we can customize the final schema
    'PREPROCESSING_HOOKS': ['SistemaCompras.api_docs.preprocessing_filter_spec'],
    'POSTPROCESSING_HOOKS': ['SistemaCompras.api_docs.postprocessing_hook'],
    'COMPONENT_SPLIT_REQUEST': True,
    'COMPONENT_NO_READ_ONLY_REQUIRED': True,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'defaultModelsExpandDepth': 2,
        'defaultModelExpandDepth': 2,
        'docExpansion': 'none',
        'filter': True,
        'showExtensions': True,
        'showCommonExtensions': True,
        'tryItOutEnabled': True,
    },
    'REDOC_UI_SETTINGS': {
        'hideDownloadButton': False,
        'hideHostname': False,
        'hideLoading': False,
        'hideSchemaPattern': True,
        'scrollYOffset': 0,
        'suppressWarnings': True,
        'theme': {
            'colors': {
                'primary': {
                    'main': "#8bd219"
                }
            },
            'typography': {
                'fontSize': '14px',
                'lineHeight': '1.5em',
                'code': {
                    'fontSize': '13px',
                    'fontFamily': 'Courier, monospace'
                },
                'headings': {
                    'fontFamily': 'Montserrat, sans-serif',
                    'fontWeight': '400'
                }
            }
        }
    }
}

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'JWT Authorization header using the Bearer scheme. Example: "Authorization: Bearer {token}"'
        }
    },
    'USE_SESSION_AUTH': False,
    'JSON_EDITOR': True,
    'SUPPORTED_SUBMIT_METHODS': [
        'get',
        'post',
        'put',
        'delete',
        'patch'
    ],
    'OPERATIONS_SORTER': 'alpha',
    'TAGS_SORTER': 'alpha',
    'DOC_EXPANSION': 'none',
    'DEEP_LINKING': True,
    'SHOW_EXTENSIONS': True,
    'DEFAULT_MODEL_DEPTH': 3,
    'DEFAULT_MODEL_RENDERING': 'example'
}

# Configuración de Redis
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASS = os.getenv('REDIS_PASSWORD', '')

# Construir la URL de Redis correctamente con o sin contraseña
if REDIS_PASS:
    REDIS_URL = f"redis://:{REDIS_PASS}@{REDIS_HOST}:{REDIS_PORT}/1"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"

# Configuración optimizada de Cache con fallback inteligente

# Variable global para evitar múltiples tests de Redis
_redis_test_done = False
_redis_available = False


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
        # Test con autenticación si está configurada
        if REDIS_PASS:
            client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASS,
                socket_connect_timeout=1,
                socket_timeout=1,
                db=1
            )
        else:
            client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                socket_connect_timeout=1,
                socket_timeout=1,
                db=1
            )

        # Test simple de ping
        client.ping()
        _redis_available = True

    except Exception as e:
        _redis_available = False
        print(f"⚠️  Redis no disponible ({e}), usando cache en memoria local")
    finally:
        _redis_test_done = True

    return _redis_available


# Configurar cache basado en disponibilidad de Redis
if is_redis_available():
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KWARGS": {
                    "retry_on_timeout": True,
                    "socket_keepalive": True,
                    "socket_keepalive_options": {},
                    "max_connections": 50,
                },
                "IGNORE_EXCEPTIONS": True,
            }
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'sistema-compras-cache',
            'OPTIONS': {
                'MAX_ENTRIES': 1000,
                'CULL_FREQUENCY': 3,
            }
        }
    }

# Configuración de Celery con Redis como broker y backend
if REDIS_PASS:
    CELERY_BROKER_URL = f"redis://:{REDIS_PASS}@{REDIS_HOST}:{REDIS_PORT}/2"
    CELERY_RESULT_BACKEND = f"redis://:{REDIS_PASS}@{REDIS_HOST}:{REDIS_PORT}/2"
else:
    CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/2"
    CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/2"

# Serialización
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Zona horaria
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Conf Task
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 60 * 60  # 60 minutos
CELERY_TASK_SOFT_TIME_LIMIT = 45 * 60  # 45 minutos
CELERY_RESULT_EXPIRES = 60 * 60  # 1 hora

# Workers
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100

# Configuraciones adicionales para optimización
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True

# Configuración de routing para analytics
CELERY_TASK_ROUTES = {
    'api.analytics.tasks.*': {
        'queue': 'analytics',
        'routing_key': 'analytics',
    },
}

# Configuración de queues
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_QUEUES = {
    'default': {
        'exchange': 'default',
        'routing_key': 'default',
    },
    'analytics': {
        'exchange': 'analytics',
        'routing_key': 'analytics',
    },
}
