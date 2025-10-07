# 🧪 Guía de Testing

Documentación completa del sistema de testing con Pytest y mejores prácticas.

## 📋 Tabla de Contenidos

- [Visión General](#visión-general)
- [Configuración](#configuración)
- [Ejecutar Tests](#ejecutar-tests)
- [Estructura de Tests](#estructura-de-tests)
- [Factories](#factories)
- [Mejores Prácticas](#mejores-prácticas)
- [Coverage](#coverage)

---

## Visión General

El proyecto utiliza **Pytest** como framework principal de testing, con más de **300 tests** cubriendo todos los módulos.

### Stack de Testing

- **Pytest 8.4.1**: Framework de testing moderno
- **Factory Boy 3.3.3**: Generación de datos de prueba
- **Faker 37.8.0**: Datos realistas
- **pytest-django 4.9.0**: Integración Django
- **pytest-cov 6.0.0**: Cobertura de código
- **pytest-xdist 3.6.1**: Ejecución paralela

### Métricas Actuales

```
Tests: 300+
Coverage: ~85%
Tiempo: ~45s (paralelo)
```

**📚 Referencia**: [Pytest Documentation](https://docs.pytest.org/)

---

## Configuración

### pytest.ini

Configuración principal en `API_Compras/pytest.ini`:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = SistemaCompras.settings
python_files = tests.py test_*.py *_tests.py
python_classes = Test*
python_functions = test_*

addopts =
    --reuse-db
    --nomigrations
    --cov=api
    --cov-report=html
    --cov-report=xml
    --cov-report=term-missing
    -v
    -n auto

markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    smoke: marks tests as smoke tests
```

**Opciones clave**:
- `--reuse-db`: Reutiliza DB de test (más rápido)
- `--nomigrations`: Skip migraciones (mucho más rápido)
- `--cov=api`: Cobertura solo de carpeta `api`
- `-n auto`: Ejecuta en paralelo (usa todos los CPU cores)

### pytest_no_coverage.ini

Para ejecución rápida sin coverage:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = SistemaCompras.settings
python_files = tests.py test_*.py *_tests.py

addopts =
    --reuse-db
    --nomigrations
    -v
    -n auto
```

**Uso**:
```bash
pytest -c pytest_no_coverage.ini
```

### conftest.py

Fixtures compartidas en `api/conftest.py`:

```python
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def api_client():
    """Cliente API de DRF"""
    return APIClient()

@pytest.fixture
def authenticated_client(api_client, user):
    """Cliente autenticado con JWT"""
    from rest_framework_simplejwt.tokens import RefreshToken
    
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client

@pytest.fixture
def user():
    """Usuario de prueba"""
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123'
    )

@pytest.fixture
def admin_user():
    """Usuario administrador"""
    return User.objects.create_superuser(
        email='admin@example.com',
        password='adminpass123'
    )
```

---

## Ejecutar Tests

### Todos los Tests

```bash
# Con coverage completo
pytest

# Sin coverage (más rápido)
pytest -c pytest_no_coverage.ini

# Sin captura de output (ver prints)
pytest -s
```

### Tests Específicos

```bash
# Módulo específico
pytest api/products/tests/

# Archivo específico
pytest api/products/tests/test_views.py

# Test específico
pytest api/products/tests/test_views.py::test_list_products

# Clase específica
pytest api/products/tests/test_views.py::TestProductViewSet

# Método específico
pytest api/products/tests/test_views.py::TestProductViewSet::test_create_product
```

### Con Marcadores

```bash
# Solo tests rápidos
pytest -m "not slow"

# Solo tests de integración
pytest -m integration

# Solo tests unitarios
pytest -m unit

# Smoke tests
pytest -m smoke
```

### Debugging

```bash
# Detenerse en el primer error
pytest -x

# Ver locals en failures
pytest -l

# Modo verbose
pytest -vv

# Con pdb en failures
pytest --pdb

# Con pudb (mejor debugger)
pytest --pdb --pdbcls=pudb.debugger:Debugger
```

### Paralelo

```bash
# Usar todos los cores
pytest -n auto

# Usar 4 workers
pytest -n 4

# Secuencial (default)
pytest -n 0
```

---

## Estructura de Tests

### Organización

```
api/
├── products/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py          # Fixtures específicas de productos
│   │   ├── test_models.py       # Tests de modelos
│   │   ├── test_serializers.py  # Tests de serializers
│   │   ├── test_views.py        # Tests de vistas
│   │   └── test_permissions.py  # Tests de permisos
│   └── factories.py             # Factories de productos
├── purchases/
│   └── tests/
│       ├── test_models.py
│       ├── test_views.py
│       └── test_services.py     # Tests de lógica de negocio
└── conftest.py                  # Fixtures globales
```

### Test de Modelo

```python
# api/products/tests/test_models.py
import pytest
from decimal import Decimal
from api.products.models import Product

@pytest.mark.django_db
class TestProductModel:
    """Tests del modelo Product"""
    
    def test_create_product(self, category):
        """Crea un producto correctamente"""
        product = Product.objects.create(
            name='Laptop Dell',
            description='High performance laptop',
            price=Decimal('999.99')
        )
        product.categories.add(category)
        
        assert product.name == 'Laptop Dell'
        assert product.price == Decimal('999.99')
        assert product.categories.count() == 1
    
    def test_product_str(self, product):
        """__str__ retorna el nombre"""
        assert str(product) == product.name
    
    def test_price_validation(self):
        """Precio no puede ser negativo"""
        with pytest.raises(ValidationError):
            product = Product(name='Test', price=Decimal('-10.00'))
            product.full_clean()
```

### Test de Serializer

```python
# api/products/tests/test_serializers.py
import pytest
from decimal import Decimal
from api.products.serializers import ProductSerializer

@pytest.mark.django_db
class TestProductSerializer:
    """Tests del serializer de Product"""
    
    def test_serialize_product(self, product):
        """Serializa producto correctamente"""
        serializer = ProductSerializer(product)
        
        assert serializer.data['id'] == product.id
        assert serializer.data['name'] == product.name
        assert Decimal(serializer.data['price']) == product.price
    
    def test_deserialize_valid_data(self, category):
        """Deserializa datos válidos"""
        data = {
            'name': 'New Product',
            'description': 'Test description',
            'price': '99.99',
            'categories': [category.id]
        }
        
        serializer = ProductSerializer(data=data)
        assert serializer.is_valid()
        
        product = serializer.save()
        assert product.name == 'New Product'
        assert product.price == Decimal('99.99')
    
    def test_invalid_price(self):
        """Rechaza precio inválido"""
        data = {
            'name': 'Product',
            'price': 'invalid'
        }
        
        serializer = ProductSerializer(data=data)
        assert not serializer.is_valid()
        assert 'price' in serializer.errors
```

### Test de Vista

```python
# api/products/tests/test_views.py
import pytest
from rest_framework import status

@pytest.mark.django_db
class TestProductViewSet:
    """Tests de ProductViewSet"""
    
    def test_list_products_unauthenticated(self, api_client):
        """No permite listar sin autenticación"""
        response = api_client.get('/api/v2/products/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_list_products_authenticated(self, authenticated_client, product_factory):
        """Lista productos autenticado"""
        product_factory.create_batch(5)
        
        response = authenticated_client.get('/api/v2/products/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 5
        assert len(response.data['results']) == 5
    
    def test_create_product(self, authenticated_client, category):
        """Crea producto correctamente"""
        data = {
            'name': 'New Laptop',
            'description': 'Test',
            'price': '1299.99',
            'categories': [category.id]
        }
        
        response = authenticated_client.post('/api/v2/products/', data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Laptop'
        assert 'id' in response.data
    
    def test_update_product(self, authenticated_client, product):
        """Actualiza producto correctamente"""
        data = {'name': 'Updated Name'}
        
        response = authenticated_client.patch(
            f'/api/v2/products/{product.id}/',
            data
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Name'
    
    def test_delete_product(self, authenticated_client, product):
        """Elimina producto correctamente"""
        response = authenticated_client.delete(f'/api/v2/products/{product.id}/')
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Product.objects.filter(id=product.id).exists()
```

### Test de Servicio

```python
# api/purchases/tests/test_services.py
import pytest
from decimal import Decimal
from api.services import create_purchase_with_details

@pytest.mark.django_db
class TestPurchaseService:
    """Tests de servicios de compras"""
    
    def test_create_purchase_success(self, user, product, storage_location):
        """Crea compra exitosamente"""
        purchase_data = {
            'user': user,
            'details': [
                {
                    'product': product,
                    'quantity': 2,
                    'unit_price': product.price
                }
            ]
        }
        
        purchase = create_purchase_with_details(purchase_data)
        
        assert purchase.id is not None
        assert purchase.user == user
        assert purchase.details.count() == 1
        assert purchase.total > Decimal('0')
    
    def test_create_purchase_insufficient_stock(self, user, product):
        """Falla si no hay stock suficiente"""
        product.stock = 1
        product.save()
        
        purchase_data = {
            'user': user,
            'details': [
                {
                    'product': product,
                    'quantity': 10  # Más que el stock
                }
            ]
        }
        
        with pytest.raises(ValidationError, match="Insufficient stock"):
            create_purchase_with_details(purchase_data)
```

---

## Factories

### Factory Boy

Generación consistente de datos de prueba usando **Factory Boy**.

**📚 Referencia**: [Factory Boy Docs](https://factoryboy.readthedocs.io/)

### Ejemplo: ProductFactory

```python
# api/products/factories.py
import factory
from factory import fuzzy
from decimal import Decimal
from api.products.models import Product
from api.categories.factories import CategoryFactory

class ProductFactory(factory.django.DjangoModelFactory):
    """Factory para Product"""
    
    class Meta:
        model = Product
    
    name = factory.Faker('word')
    description = factory.Faker('text', max_nb_chars=200)
    price = fuzzy.FuzzyDecimal(10.0, 1000.0, 2)
    
    @factory.post_generation
    def categories(self, create, extracted, **kwargs):
        """Agrega categorías después de crear el producto"""
        if not create:
            return
        
        if extracted:
            for category in extracted:
                self.categories.add(category)
        else:
            # Por defecto, agregar una categoría
            self.categories.add(CategoryFactory())
```

**Uso**:

```python
# Crear un producto
product = ProductFactory()

# Con atributos específicos
product = ProductFactory(name='Laptop Dell', price=Decimal('999.99'))

# Con relaciones
category1 = CategoryFactory(name='Electronics')
category2 = CategoryFactory(name='Computers')
product = ProductFactory(categories=(category1, category2))

# Crear batch
products = ProductFactory.create_batch(10)

# Build sin guardar en DB
product = ProductFactory.build()
```

### Factories Completas

```python
# api/users/factories.py
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    
    email = factory.Faker('email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')

# api/purchases/factories.py
class PurchaseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Purchase
    
    user = factory.SubFactory(UserFactory)
    purchase_date = factory.Faker('date_time_this_year')
    total = fuzzy.FuzzyDecimal(100.0, 5000.0, 2)
    installments = fuzzy.FuzzyInteger(1, 12)

class PurchaseDetailFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PurchaseDetail
    
    purchase = factory.SubFactory(PurchaseFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = fuzzy.FuzzyInteger(1, 10)
    unit_price = fuzzy.FuzzyDecimal(10.0, 500.0, 2)
```

---

## Mejores Prácticas

### 1. Usar Fixtures y Factories

**❌ Evitar**:
```python
def test_create_purchase():
    user = User.objects.create(email='test@example.com')
    product = Product.objects.create(name='Laptop', price=999.99)
    # ... setup repetitivo
```

**✅ Preferir**:
```python
def test_create_purchase(user, product):
    # user y product vienen de fixtures/factories
    purchase = Purchase.objects.create(user=user, total=product.price)
```

### 2. Usar Marcadores

```python
@pytest.mark.slow
def test_large_report_generation():
    """Test que toma mucho tiempo"""
    pass

@pytest.mark.integration
def test_full_purchase_flow():
    """Test de integración completo"""
    pass
```

### 3. Parametrize para Múltiples Casos

```python
@pytest.mark.parametrize('price,expected', [
    (Decimal('10.00'), Decimal('11.50')),  # +15% tax
    (Decimal('100.00'), Decimal('115.00')),
    (Decimal('0.01'), Decimal('0.01')),    # Min tax
])
def test_calculate_tax(price, expected):
    assert calculate_tax(price) == expected
```

### 4. Nombres Descriptivos

**❌ Evitar**:
```python
def test_1():
    pass

def test_product():
    pass
```

**✅ Preferir**:
```python
def test_create_product_with_valid_data():
    pass

def test_product_price_validation_rejects_negative():
    pass
```

### 5. Arrange-Act-Assert

```python
def test_update_product_price(authenticated_client, product):
    # Arrange - Preparar
    new_price = Decimal('1499.99')
    data = {'price': str(new_price)}
    
    # Act - Actuar
    response = authenticated_client.patch(
        f'/api/v2/products/{product.id}/',
        data
    )
    
    # Assert - Verificar
    assert response.status_code == status.HTTP_200_OK
    product.refresh_from_db()
    assert product.price == new_price
```

### 6. Test de Signals

```python
@pytest.mark.django_db
def test_purchase_sends_email(user, product, mailoutbox):
    """Verifica que se envía email al crear compra"""
    purchase = Purchase.objects.create(user=user, total=100)
    
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == [user.email]
    assert 'Purchase Confirmed' in mailoutbox[0].subject
```

### 7. Deshabilitar Signals en Tests

```python
# Con decorator
from django.test import override_settings

@override_settings(DISABLE_SIGNALS=True)
def test_bulk_create_without_emails():
    """Crea muchos registros sin enviar emails"""
    PurchaseFactory.create_batch(100)
```

---

## Coverage

### Generar Reporte

```bash
# HTML
pytest --cov=api --cov-report=html

# Terminal
pytest --cov=api --cov-report=term-missing

# XML (para CI/CD)
pytest --cov=api --cov-report=xml
```

### Ver Reporte HTML

```bash
# Abrir en navegador
open htmlcov/index.html  # macOS
start htmlcov/index.html # Windows
xdg-open htmlcov/index.html # Linux
```

### Coverage por Módulo

```bash
pytest --cov=api.products --cov-report=term-missing
pytest --cov=api.purchases --cov-report=term-missing
```

### Configurar Mínimo Coverage

```ini
# pytest.ini
[pytest]
addopts =
    --cov=api
    --cov-fail-under=80
```

Fallará si coverage < 80%.

---

## Próximos Pasos

Para información complementaria:

- **Arquitectura**: Ver [Architecture](ARCHITECTURE.md)
- **Desarrollo**: Ver [Development](DEVELOPMENT.md)
- **CI/CD**: Ver documentación de GitHub Actions

---

**📚 Volver a**: [README principal](../README.md)
