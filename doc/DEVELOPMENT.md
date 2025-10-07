# 🛠️ Guía de Desarrollo

Documentación para desarrolladores que trabajan en el proyecto.

## 📋 Tabla de Contenidos

- [Setup Inicial](#setup-inicial)
- [Workflows Comunes](#workflows-comunes)
- [Debugging](#debugging)
- [Comandos Útiles](#comandos-útiles)
- [Extensiones Recomendadas](#extensiones-recomendadas)
- [Convenciones de Código](#convenciones-de-código)

---

## Setup Inicial

### Pre-requisitos

- **Python 3.12+**
- **Docker Desktop** (opcional pero recomendado)
- **Git**
- **IDE**: VS Code, PyCharm o similar

### Clonar Repositorio

```bash
git clone https://github.com/tu-usuario/SistemaCompra.git
cd SistemaCompra
```

### Setup con Docker (Recomendado)

```bash
# Levantar todos los servicios
docker-compose up -d

# Verificar que estén corriendo
docker-compose ps

# Ver logs
docker-compose logs -f backend

# Acceder
http://localhost:8000/api/schema/swagger-ui/
```

### Setup Manual

Ver guía completa en [INSTALLATION.md](INSTALLATION.md#instalación-manual).

**Resumen**:
```bash
# 1. Crear virtualenv
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 2. Instalar dependencias
cd API_Compras
pip install -r requirements.txt

# 3. Variables de entorno
cp .env.example .env
# Editar .env con tus valores

# 4. Migraciones
python manage.py migrate

# 5. Crear superuser
python manage.py createsuperuser

# 6. Runserver
python manage.py runserver
```

---

## Workflows Comunes

### Crear Nueva App Django

```bash
# Dentro de API_Compras/
python manage.py startapp my_new_app

# Mover a carpeta api/
mv my_new_app api/

# Registrar en settings.py
INSTALLED_APPS = [
    # ...
    'api.my_new_app',
]
```

### Crear Modelo

```python
# api/my_new_app/models.py
from django.db import models

class MyModel(models.Model):
    """
    Descripción del modelo.
    
    Attributes:
        name: Nombre del elemento
        created_at: Fecha de creación
    """
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'my_new_app_mymodel'
        verbose_name = 'My Model'
        verbose_name_plural = 'My Models'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
```

### Crear Migraciones

```bash
# Generar archivo de migración
python manage.py makemigrations

# Ver SQL sin ejecutar
python manage.py sqlmigrate my_new_app 0001

# Ejecutar migraciones
python manage.py migrate

# Rollback
python manage.py migrate my_new_app 0001  # Volver a migración específica
```

### Crear Serializer

```python
# api/my_new_app/serializers.py
from rest_framework import serializers
from .models import MyModel

class MyModelSerializer(serializers.ModelSerializer):
    """
    Serializer para MyModel.
    
    Campos:
        - id: Identificador único
        - name: Nombre del elemento
        - created_at: Fecha de creación
    """
    
    class Meta:
        model = MyModel
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def validate_name(self, value):
        """Valida que el nombre no esté vacío"""
        if not value.strip():
            raise serializers.ValidationError("Name cannot be empty")
        return value
```

### Crear ViewSet

```python
# api/my_new_app/views.py
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import MyModel
from .serializers import MyModelSerializer

class MyModelViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestión de MyModel.
    
    list:
        Retorna lista de elementos
    
    create:
        Crea un nuevo elemento
    
    retrieve:
        Retorna detalle de un elemento
    
    update:
        Actualiza un elemento completo
    
    partial_update:
        Actualiza campos específicos
    
    destroy:
        Elimina un elemento
    """
    queryset = MyModel.objects.all()
    serializer_class = MyModelSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name']
    search_fields = ['name']
    ordering_fields = ['created_at', 'name']
```

### Registrar URLs

```python
# api/my_new_app/urls.py
from rest_framework.routers import DefaultRouter
from .views import MyModelViewSet

router = DefaultRouter()
router.register(r'items', MyModelViewSet, basename='mymodel')

urlpatterns = router.urls

# api/urls.py (incluir en URLs principales)
from django.urls import path, include

urlpatterns = [
    # ...
    path('my-new-app/', include('api.my_new_app.urls')),
]
```

### Crear Tests

```python
# api/my_new_app/tests/test_views.py
import pytest
from rest_framework import status
from .factories import MyModelFactory

@pytest.mark.django_db
class TestMyModelViewSet:
    """Tests de MyModelViewSet"""
    
    def test_list_items(self, authenticated_client):
        """Lista items correctamente"""
        MyModelFactory.create_batch(5)
        
        response = authenticated_client.get('/api/v2/my-new-app/items/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 5
    
    def test_create_item(self, authenticated_client):
        """Crea item correctamente"""
        data = {'name': 'New Item'}
        
        response = authenticated_client.post('/api/v2/my-new-app/items/', data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Item'
```

### Crear Factory

```python
# api/my_new_app/factories.py
import factory
from .models import MyModel

class MyModelFactory(factory.django.DjangoModelFactory):
    """Factory para MyModel"""
    
    class Meta:
        model = MyModel
    
    name = factory.Faker('word')
```

---

## Debugging

### Django Shell Plus

```bash
# Shell interactivo con todos los modelos importados
python manage.py shell_plus

# Con IPython
python manage.py shell_plus --ipython
```

**Ejemplo**:
```python
# Ya están importados todos los modelos
>>> from api.products.models import Product
>>> Product.objects.count()
45

# Ver queries SQL ejecutadas
>>> from django.db import connection
>>> Product.objects.filter(name__icontains='laptop')
>>> print(connection.queries[-1]['sql'])
```

### Django Debug Toolbar

Instalado en el proyecto, muestra en el navegador:
- Queries SQL ejecutadas
- Templates renderizados
- Tiempo de respuesta
- Cache hits/misses

**Acceso**: Barra lateral en navegador cuando `DEBUG=True`

### Logs

```python
# En cualquier archivo
import logging

logger = logging.getLogger(__name__)

def my_function():
    logger.debug("Mensaje de debug")
    logger.info("Mensaje informativo")
    logger.warning("Advertencia")
    logger.error("Error")
```

**Ver logs**:
```bash
# Docker
docker-compose logs -f backend

# Manual
tail -f logs/debug.log
tail -f logs/errors.log
```

### VS Code Debugger

Configuración en `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Django: Debug",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/API_Compras/manage.py",
      "args": ["runserver"],
      "django": true,
      "justMyCode": true
    },
    {
      "name": "Pytest: Debug",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["-v", "-s"],
      "django": true,
      "justMyCode": false
    }
  ]
}
```

---

## Comandos Útiles

### Django Management Commands

```bash
# Crear superuser
python manage.py createsuperuser

# Cambiar contraseña
python manage.py changepassword user@example.com

# Eliminar sesiones expiradas
python manage.py clearsessions

# Recolectar archivos estáticos
python manage.py collectstatic --noinput

# Verificar deployment
python manage.py check --deploy

# Generar datos de prueba (custom command)
python manage.py generate_data
```

### Database

```bash
# Backup MySQL
docker-compose exec db mysqldump -u root -proot compras_db > backup.sql

# Restore
docker-compose exec -T db mysql -u root -proot compras_db < backup.sql

# Shell MySQL
docker-compose exec db mysql -u root -proot compras_db
```

### Cache

```bash
# Limpiar cache
python manage.py clear_cache

# Precalentar cache (custom command)
python manage.py warm_cache
```

### Celery

```bash
# Iniciar worker (desarrollo)
cd API_Compras
celery -A SistemaCompras worker --loglevel=info

# Iniciar beat scheduler
celery -A SistemaCompras beat --loglevel=info

# Flower (monitoreo web)
celery -A SistemaCompras flower --port=5555

# Ver tareas encoladas
celery -A SistemaCompras inspect active
```

### Docker

```bash
# Reconstruir contenedores
docker-compose up -d --build

# Ver logs de servicio específico
docker-compose logs -f celery_worker

# Ejecutar comando en contenedor
docker-compose exec backend python manage.py shell

# Limpiar contenedores y volúmenes
docker-compose down -v
```

---

## Extensiones Recomendadas

### VS Code

```json
// .vscode/extensions.json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.black-formatter",
    "charliermarsh.ruff",
    "mtxr.sqltools",
    "mtxr.sqltools-driver-mysql",
    "humao.rest-client",
    "batisteo.vscode-django",
    "redhat.vscode-yaml",
    "ms-azuretools.vscode-docker"
  ]
}
```

### PyCharm

Plugins recomendados:
- **Envfile**: Soporte para archivos `.env`
- **Requirements**: Gestión de dependencias
- **Markdown**: Preview de documentación
- **Database Tools**: SQL integration

---

## Convenciones de Código

### Estilo Python

Seguimos **PEP 8** con algunas modificaciones:

```python
# Longitud de línea: 100 caracteres (no 79)
MAX_LINE_LENGTH = 100

# Imports ordenados con isort
from django.db import models  # Django
from rest_framework import serializers  # Third party
from api.users.models import User  # Local
```

### Docstrings

Formato Google Style:

```python
def calculate_total(items, tax_rate=0.15):
    """
    Calcula el total de una compra incluyendo impuestos.
    
    Args:
        items (list): Lista de items de la compra
        tax_rate (float, optional): Tasa de impuesto. Por defecto 0.15
    
    Returns:
        Decimal: Total calculado con impuestos
    
    Raises:
        ValueError: Si items está vacío
    
    Examples:
        >>> calculate_total([{'price': 100}, {'price': 200}])
        Decimal('345.00')
    """
    if not items:
        raise ValueError("Items cannot be empty")
    
    subtotal = sum(item['price'] for item in items)
    return subtotal * (1 + tax_rate)
```

### Nombres

```python
# Variables y funciones: snake_case
user_count = 10
def get_active_users():
    pass

# Clases: PascalCase
class ProductSerializer:
    pass

# Constantes: UPPER_CASE
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB
DEFAULT_PAGE_SIZE = 20
```

### Commits

Formato de mensajes:

```
<tipo>(<scope>): <descripción>

[cuerpo opcional]

[footer opcional]
```

**Tipos**:
- `feat`: Nueva funcionalidad
- `fix`: Corrección de bug
- `docs`: Cambios en documentación
- `style`: Formato (no afecta código)
- `refactor`: Refactorización
- `test`: Tests
- `chore`: Tareas de mantenimiento

**Ejemplos**:
```
feat(products): agregar filtro por categoría

Agrega endpoint para filtrar productos por categoría
con paginación.

Closes #42

---

fix(payments): corregir cálculo de mora

La mora no se calculaba correctamente para cuotas
vencidas hace más de 30 días.

---

docs(readme): actualizar instrucciones de instalación
```

---

## Próximos Pasos

Para información complementaria:

- **Arquitectura**: Ver [Architecture](ARCHITECTURE.md)
- **Testing**: Ver [Testing](TESTING.md)
- **API Reference**: [Swagger UI](http://localhost:8000/api/schema/swagger-ui/)

---

**📚 Volver a**: [README principal](../README.md)
