"""
Configuraciones y hooks para la documentación de la API con drf-spectacular.

Este archivo contiene funciones de preprocesamiento y postprocesamiento
para personalizar la documentación OpenAPI generada automáticamente.

Basado en la documentación oficial de drf-spectacular:
https://drf-spectacular.readthedocs.io/en/latest/customization.html#preprocessing-hooks
"""
from drf_spectacular.utils import extend_schema_view, extend_schema
from drf_spectacular.openapi import AutoSchema
import logging

logger = logging.getLogger(__name__)


def preprocessing_filter_spec(endpoints):
    """
    Filtra y organiza los endpoints antes de generar la documentación.

    Esta función se ejecuta antes de que drf-spectacular genere la documentación
    y permite filtrar endpoints no deseados, agregar metadatos adicionales
    o reorganizar la estructura de la documentación.

    Args:
        endpoints (list): Lista de tuplas (path, path_regex, method, callback)
                         detectados por drf-spectacular

    Returns:
        list: Lista filtrada y procesada de endpoints

    Raises:
        Exception: Si hay errores durante el filtrado de endpoints

    References:
        - https://drf-spectacular.readthedocs.io/en/latest/customization.html#preprocessing-hooks
    """
    try:
        filtered = []

        # Filtrar endpoints que no queremos mostrar en la documentación
        excluded_paths = [
            '/admin/',
            '/api-auth/',
            '/static/',
            '/media/',
            '/__debug__/',  # Django Debug Toolbar
        ]

        for (path, path_regex, method, callback) in endpoints:
            try:
                # Excluir paths administrativos y de desarrollo
                if any(path.startswith(excluded) for excluded in excluded_paths):
                    logger.debug(f"Excluyendo endpoint: {method} {path}")
                    continue

                # Solo procesar endpoints que tengan callback válido
                if callback is None:
                    logger.warning(
                        f"Callback nulo para endpoint: {method} {path}")
                    continue

                # Agregar el endpoint filtrado
                filtered.append((path, path_regex, method, callback))
                logger.debug(f"Endpoint incluido: {method} {path}")

            except Exception as e:
                logger.error(f"Error procesando endpoint {path}: {str(e)}")
                continue

        logger.info(
            f"Filtrados {len(filtered)} endpoints de {len(endpoints)} totales")
        return filtered

    except Exception as e:
        logger.error(f"Error en preprocessing_filter_spec: {str(e)}")
        # En caso de error, retornar los endpoints originales
        return endpoints


def postprocessing_hook(result, generator, request, public):
    """
    Modifica el esquema OpenAPI después de su generación.

    Esta función permite personalizar el esquema final antes de ser
    servido a los clientes de documentación como Swagger UI y ReDoc.

    Args:
        result (dict): Esquema OpenAPI generado
        generator: Instancia del generador de esquemas de drf-spectacular
        request: Request HTTP actual (puede ser None)
        public (bool): Si es una vista pública o no

    Returns:
        dict: Esquema OpenAPI modificado

    Raises:
        Exception: Si hay errores durante la modificación del esquema

    References:
        - https://drf-spectacular.readthedocs.io/en/latest/customization.html#postprocessing-hooks
        - https://spec.openapis.org/oas/v3.0.3
    """
    try:
        # Verificar que result es un diccionario válido
        if not isinstance(result, dict):
            logger.error(
                f"Resultado inválido en postprocessing_hook: {type(result)}")
            return result

        # Asegurar que 'info' existe
        if 'info' not in result:
            result['info'] = {}

        # Agregar información adicional al esquema
        result['info'].update({
            'title': 'Sistema de Compras API',
            'version': '2.0.0',
            'description': '''

Una API REST completa para gestión de compras, inventario y pagos construida con Django REST Framework.

## 📋 Características principales

- ✅ **Gestión de usuarios** con autenticación JWT
- 🛍️ **Catálogo de productos** con categorías y promociones
- 🛒 **Sistema de compras** con cuotas flexibles
- 💰 **Procesamiento de pagos** múltiples métodos
- 📦 **Control de inventario** en tiempo real
- 🎯 **Sistema de promociones** avanzado
- 🔐 **Seguridad robusta** con permisos granulares

## 🚀 Comenzando

1. Obtén tus credenciales de acceso
2. Autentica usando el endpoint `/api/v2/token`
3. Incluye el token JWT en tus peticiones
4. ¡Explora los endpoints disponibles!

## 📞 Soporte

¿Necesitas ayuda? Contacta a nuestro equipo de soporte técnico.
            ''',
            'termsOfService': 'https://nataliullacoder.com/terms',
            'x-logo': {
                'url': 'https://nataliullacoder.com/logo.png',
                'altText': 'Sistema de Compras API',
                'backgroundColor': '#FFFFFF'
            }
        })

        # Personalizar la información de contacto
        result['info']['contact'] = {
            'name': '👨‍💻 Guillermo Natali Ulla - Soporte Técnico',
            'url': 'https://nataliullacoder.com/',
            'email': 'guillermonatali22@gmail.com',
            'x-twitter': '@nataliullacoder'
        }

        # Información de licencia
        result['info']['license'] = {
            'name': 'MIT License',
            'url': 'https://opensource.org/licenses/MIT'
        }

        # Agregar enlaces externos útiles
        result['externalDocs'] = {
            'description': '📚 Documentación completa del proyecto en GitHub',
            'url': 'https://github.com/guille-nat/Api_Compras'
        }

        # Inicializar components si no existe
        if 'components' not in result:
            result['components'] = {}

        if 'securitySchemes' not in result['components']:
            result['components']['securitySchemes'] = {}

        # Personalizar esquemas de seguridad JWT
        result['components']['securitySchemes']['bearerAuth'] = {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
            'description': '''
## 🔑 Autenticación JWT

Para acceder a los endpoints protegidos, necesitas incluir un token JWT válido en el header Authorization.

### 📝 Pasos para autenticarse:

1. **Obtener credenciales**: Regístrate usando `/api/v2/users/` o solicita credenciales al administrador
2. **Solicitar token**: Envía una petición POST a `/api/v2/token/` con tu username y password
3. **Usar token**: Incluye el token en todas las peticiones protegidas como: `Authorization: Bearer <tu_token>`
4. **Renovar token**: Cuando expire, usa el refresh token en `/api/v2/token/refresh/`

### ⚠️ Consideraciones importantes:
- Los tokens de acceso expiran en 5 minutos
- Los tokens de refresh expiran en 1 día
- Guarda los tokens de forma segura
- No incluyas tokens en URLs o logs
- Renueva proactivamente antes del vencimiento

### 🔧 Ejemplo de uso:
```bash
# 1. Obtener token
curl -X POST /api/v2/token/ \\
  -H "Content-Type: application/json" \\
  -d '{"username": "tu_usuario", "password": "tu_contraseña"}'

# 2. Usar token en peticiones
curl -X GET /api/v2/users/ \\
  -H "Authorization: Bearer <tu_access_token>"
```
            '''
        }

        # Esquema para API Key alternativo (si se usa)
        result['components']['securitySchemes']['apiKey'] = {
            'type': 'apiKey',
            'in': 'header',
            'name': 'X-API-Key',
            'description': 'API Key para integraciones externas (alternativo a JWT)'
        }

        # Configurar seguridad global
        if 'security' not in result:
            result['security'] = []

        # JWT como método de autenticación principal
        if {'bearerAuth': []} not in result['security']:
            result['security'].append({'bearerAuth': []})

        # Agregar servidores de ejemplo
        if 'servers' not in result:
            result['servers'] = []

        # Solo agregar servidores si no existen
        existing_urls = [server.get('url', '') for server in result['servers']]

        servers_to_add = [
            {
                'url': 'http://localhost:8000',
                'description': '🔧 Servidor de Desarrollo Local'
            },
            {
                'url': 'https://api.sistemacompras.dev',
                'description': '🧪 Servidor de Pruebas (Testing)'
            },
            {
                'url': 'https://api.sistemacompras.com',
                'description': '🚀 Servidor de Producción'
            }
        ]

        for server in servers_to_add:
            if server['url'] not in existing_urls:
                result['servers'].append(server)

        # Agregar metadatos adicionales para herramientas
        # Construimos dinámicamente x-tagGroups para que ReDoc agrupe los
        # tags por categoría y muestre las sub-etiquetas Public / Authenticated / Admin
        if 'x-tagGroups' not in result:
            try:
                # import local helper that centralizes tag names
                from api.view_tags import tag_name, products_public, products_authenticated, products_admin, \
                    categories_public, categories_admin, promotions_public, promotions_admin, \
                    storage_admin, purchases_status_management, purchases_installments_management, \
                    purchases_discounts, purchases_admin, purchases_user_management, purchases_crud, \
                    products_authenticated as _prod_auth

                def flatten(lists):
                    res = []
                    for item in lists:
                        if isinstance(item, (list, tuple)):
                            res.extend(item)
                        else:
                            res.append(item)
                    return res

                result['x-tagGroups'] = []

                # Standard category groups with Public / Authenticated / Admin
                standard_cats = [
                    'Products',
                    'Categories',
                    'Promotions',
                    'Payments',
                    'Inventories',
                    'Storage Locations',
                    'Users',
                    'Authentication',
                ]

                for cat in standard_cats:
                    result['x-tagGroups'].append({'name': cat, 'tags': [
                        tag_name(cat, 'Public'),
                        tag_name(cat, 'Authenticated'),
                        tag_name(cat, 'Admin'),
                    ]})

                # Purchases: include the more granular purchase-related tags
                purchases_tags = flatten([
                    purchases_status_management(),
                    purchases_installments_management(),
                    purchases_discounts(),
                    purchases_admin(),
                    purchases_user_management(),
                    purchases_crud(),
                ])

                result['x-tagGroups'].append({'name': 'Purchases',
                                             'tags': purchases_tags})

            except Exception:
                # Fallback: mantener la configuración previa simplificada si algo falla
                result['x-tagGroups'] = [
                    {
                        'name': 'Authentication & Users',
                        'tags': ['Authentication', 'Users']
                    },
                    {
                        'name': 'Commerce',
                        'tags': ['Products', 'Purchases', 'Categories', 'Promotions']
                    }
                ]

        logger.info("Esquema OpenAPI personalizado exitosamente")
        return result

    except Exception as e:
        logger.error(f"Error en postprocessing_hook: {str(e)}")
        # En caso de error, retornar el resultado original
        return result


class CustomAutoSchema(AutoSchema):
    """
    Esquema personalizado para generar documentación más detallada.

    Esta clase extiende AutoSchema de drf-spectacular para proporcionar
    mejor documentación automática basada en los modelos y serializers.

    References:
        - https://drf-spectacular.readthedocs.io/en/latest/customization.html#step-4-auto-schema-customization
    """

    def get_tags(self):
        """
        Genera tags automáticamente basados en el path del endpoint.

        Returns:
            list: Lista de tags para el endpoint
        """
        try:
            tags = super().get_tags()

            if tags:
                return tags

            # Generar tags basados en el path
            path = self.path

            tag_mapping = {
                'token': '🔐 Autenticación',
                'users': '👥 Usuarios',
                'products': '📦 Productos',
                'purchases': '🛒 Compras',
                'payments': '💰 Pagos',
                'installments': '📊 Cuotas',
                'inventories': '🏪 Inventario',
                'categories': '🏷️ Categorías',
                'promotions': '🎯 Promociones',
                'storage-locations': '📍 Ubicaciones',
                'notification-templates': '📧 Notificaciones',
            }

            for key, tag in tag_mapping.items():
                if key in path:
                    return [tag]

            return ['📋 General']

        except Exception as e:
            logger.error(f"Error generando tags: {str(e)}")
            return ['📋 General']

    def get_operation_id(self):
        """
        Genera un operation_id más descriptivo.

        Returns:
            str: ID de la operación personalizado
        """
        try:
            # Usar el operation_id por defecto y mejorarlo
            operation_id = super().get_operation_id()

            # Si ya tiene un ID personalizado, usarlo
            if hasattr(self.view, 'operation_id'):
                return self.view.operation_id

            return operation_id

        except Exception as e:
            logger.error(f"Error generando operation_id: {str(e)}")
            return 'unknown_operation'
