# 🏗️ Arquitectura del Sistema - API Compras

Esta documentación describe la arquitectura completa del sistema, decisiones de diseño y patrones implementados.

## 📋 Tabla de Contenidos

- [Visión General](#visión-general)
- [Arquitectura de Alto Nivel](#arquitectura-de-alto-nivel)
- [Módulos del Sistema](#módulos-del-sistema)
- [Base de Datos](#base-de-datos)
- [Patrones de Diseño](#patrones-de-diseño)
- [Decisiones Técnicas](#decisiones-técnicas)

---

## Visión General

### Principios Arquitectónicos

1. **Separación de Responsabilidades**: Cada app Django tiene una responsabilidad única y bien definida
2. **Modularidad**: Componentes independientes y reutilizables
3. **Escalabilidad**: Diseño preparado para crecimiento horizontal
4. **Performance**: Cache inteligente y optimización de consultas
5. **Mantenibilidad**: Código limpio siguiendo principios SOLID

### Stack Tecnológico

```
┌─────────────────────────────────────────┐
│         Frontend (No incluido)          │
└─────────────┬───────────────────────────┘
              │ REST API (JWT)
┌─────────────▼───────────────────────────┐
│      Django REST Framework 3.15.2       │
│          (API Layer)                    │
├─────────────────────────────────────────┤
│         Django 5.1.5                    │
│      (Business Logic)                   │
├─────────────────────────────────────────┤
│  Celery 5.5.3    │    Redis 7.0        │
│  (Async Tasks)   │    (Cache/Broker)   │
├──────────────────┴─────────────────────┤
│           MySQL 9.0                     │
│        (Main Database)                  │
└─────────────────────────────────────────┘
```

---

## Arquitectura de Alto Nivel

### Diagrama de Componentes

```
┌────────────────────────────────────────────────────────────┐
│                     API Gateway (Nginx)                     │
└─────────────────────┬──────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
┌───────▼──────┐ ┌───▼────┐ ┌─────▼──────┐
│   Backend    │ │ Celery │ │   Celery   │
│   (Django)   │ │ Worker │ │    Beat    │
└───────┬──────┘ └───┬────┘ └─────┬──────┘
        │            │            │
        └────────┬───┴────────────┘
                 │
        ┌────────┼────────┐
        │        │        │
  ┌─────▼───┐ ┌─▼────┐ ┌─▼────────┐
  │  MySQL  │ │ Redis│ │  Static  │
  │    DB   │ │Cache │ │  Files   │
  └─────────┘ └──────┘ └──────────┘
```

### Flujo de una Request

```
1. Cliente → Nginx → Django
2. Django → Middleware de Cache → Check Redis
3. Si Cache Miss → Django → Business Logic
4. Business Logic → Database (MySQL)
5. Response → Cache (Redis) → Cliente
```

---

## Módulos del Sistema

### 1. 👥 Users (`api/users/`)

**Responsabilidad**: Gestión de usuarios y autenticación

**Modelos**:
- `CustomUser`: Usuario extendido con campos adicionales

**Funcionalidades**:
- Registro de usuarios
- Login/Logout con JWT
- Gestión de perfiles
- Permisos por roles

**Endpoints principales**:
```
POST   /api/v2/users/register/
POST   /api/v2/token/
POST   /api/v2/token/refresh/
GET    /api/v2/users/me/
PATCH  /api/v2/users/me/
```

### 2. 🛍️ Products (`api/products/`)

**Responsabilidad**: Catálogo de productos

**Modelos**:
- `Product`: Información del producto
- `ProductCategory`: Relación N:N con categorías

**Funcionalidades**:
- CRUD de productos
- Filtrado y búsqueda
- Gestión de categorías
- Cache agresivo (TTL: 1 hora)

**Endpoints principales**:
```
GET    /api/v2/products/
POST   /api/v2/products/
GET    /api/v2/products/{id}/
PATCH  /api/v2/products/{id}/
DELETE /api/v2/products/{id}/
```

### 3. 📂 Categories (`api/categories/`)

**Responsabilidad**: Organización jerárquica de productos

**Modelos**:
- `Category`: Categoría con soporte para jerarquías

**Funcionalidades**:
- Estructura jerárquica (parent/child)
- Validaciones de circularidad
- Cache de árboles de categorías

### 4. 🏢 Storage Locations (`api/storage_location/`)

**Responsabilidad**: Gestión de depósitos/ubicaciones

**Modelos**:
- `StorageLocation`: Ubicación física de almacenamiento

**Funcionalidades**:
- Multi-depósito
- Control de capacidad
- Validaciones de espacio

### 5. 📦 Inventories (`api/inventories/`)

**Responsabilidad**: Control de stock

**Modelos**:
- `InventoryRecord`: Stock por producto y ubicación
- `InventoryMovement`: Trazabilidad de movimientos
- `StockSnapshot`: Historial de inventario

**Funcionalidades**:
- Stock en tiempo real
- Movimientos (IN/OUT/TRANSFER)
- Alertas de stock bajo
- Snapshots históricos
- Invalidación de cache automática

**Flujo de movimiento**:
```
1. Crear InventoryMovement
2. Signal → Actualizar InventoryRecord
3. Signal → Crear StockSnapshot
4. Signal → Invalidar cache
```

### 6. 🛒 Purchases (`api/purchases/`)

**Responsabilidad**: Gestión de compras

**Modelos**:
- `Purchase`: Compra principal
- `PurchaseDetail`: Items de la compra

**Funcionalidades**:
- Compras con detalles
- Cálculo automático de totales
- Generación automática de cuotas
- Validaciones de stock
- Signals para notificaciones

**Flujo de compra**:
```
1. POST /purchases/ con detalles
2. Validar stock disponible
3. Crear Purchase + PurchaseDetails
4. Generar cuotas (Installments)
5. Actualizar inventario
6. Enviar notificación (signal)
```

### 7. 💳 Payments (`api/payments/`)

**Responsabilidad**: Sistema de pagos en cuotas

**Modelos**:
- `Installment`: Cuota individual
- `Payment`: Registro de pago
- `InstallmentAuditLog`: Auditoría de cambios

**Funcionalidades**:
- Pagos parciales y totales
- Cálculo automático de mora
- Recargos por vencimiento
- Auditoría completa
- Notificaciones automáticas

**Estados de cuota**:
```
PENDING → PAID (pago exitoso)
PENDING → OVERDUE (vencida, automático por Celery Beat)
```

**Flujo de pago**:
```
1. POST /payments/pay/
2. Validar monto y estado
3. Crear Payment
4. Actualizar Installment.state = PAID
5. InstallmentAuditLog (histórico)
6. Signal → Enviar notificación
```

### 8. 🎁 Promotions (`api/promotions/`)

**Responsabilidad**: Sistema de promociones

**Modelos**:
- `Promotion`: Promoción principal
- `PromotionRule`: Reglas de aplicación
- `PromotionScope*`: Alcance (productos, categorías, ubicaciones)

**Funcionalidades**:
- Descuentos porcentuales o fijos
- Múltiples criterios
- Validación automática de vigencia
- Aplicación en tiempo de compra

### 9. 📊 Analytics (`api/analytics/`)

**Responsabilidad**: Reportes y Business Intelligence

**Modelos**:
- `Report`: Registro de reportes generados

**Funcionalidades**:
- 6 tipos de reportes asíncronos
- Generación en background (Celery)
- Multi-formato (Excel, PNG, ZIP, JSON)
- Gráficos profesionales con Matplotlib
- Almacenamiento de archivos

**Tipos de reporte**:
1. **Rotación de productos**: Stock por ubicación
2. **Movimientos**: Entrada/salida de inventario
3. **Resumen de ventas**: Ingresos y comparativas
4. **Top productos**: Más vendidos (configurable)
5. **Métodos de pago**: Distribución de pagos
6. **Cuotas vencidas**: Mora y recargos

**Arquitectura asíncrona**:
```
Cliente → POST /reports/sales/create/
        → Celery Task encolada
        → Response inmediata con task_id
        
Cliente → GET /reports/status/{task_id}/
        → Estado: PENDING/PROCESSING/COMPLETED/FAILED

Cliente → GET /reports/{report_id}/download/
        → Archivo generado
```

### 10. 🚀 Cache (`api/cache/`)

**Responsabilidad**: Sistema de cache Redis

**Componentes**:
- `CacheManager`: Gestión centralizada
- `CacheMiddleware`: Monitoreo automático
- `cache_views.py`: Admin dashboard

**Funcionalidades**:
- Cache con TTLs configurables
- Invalidación por patrones
- Métricas en tiempo real
- Precalentamiento automático
- Fallback a LocMem

**Claves de cache**:
```python
CacheKeys = {
    'product_detail': 'product:{product_id}',
    'category_list': 'categories:all',
    'inventory_stock': 'inventory:stock:{location_id}',
    'user_purchases': 'user:{user_id}:purchases',
    # ... más claves
}
```

---

## Base de Datos

### Diagrama ER (Simplificado)

```
┌─────────────┐         ┌──────────────┐
│   User      │────────▶│  Purchase    │
└─────────────┘         └──────┬───────┘
                               │
                               │ 1:N
                               ▼
                        ┌──────────────┐
                        │PurchaseDetail│
                        └──────┬───────┘
                               │
                        ┌──────┴───────┐
                        │              │
                        ▼              ▼
                 ┌──────────┐   ┌────────────┐
                 │ Product  │   │Installment │
                 └──────┬───┘   └──────┬─────┘
                        │              │
                        │              ▼
                        │       ┌──────────┐
                        │       │ Payment  │
                        │       └──────────┘
                        │
                        ▼
              ┌──────────────────┐
              │InventoryRecord   │
              └──────────────────┘
```

### Índices Importantes

```sql
-- Búsquedas frecuentes
CREATE INDEX idx_product_name ON products (name);
CREATE INDEX idx_purchase_user ON purchases (user_id);
CREATE INDEX idx_installment_state ON installments (state);

-- Composite indexes
CREATE INDEX idx_inventory_product_location 
ON inventory_records (product_id, location_id);

-- Fechas para reportes
CREATE INDEX idx_purchase_date ON purchases (purchase_date);
CREATE INDEX idx_installment_due_date ON installments (due_date);
```

---

## Patrones de Diseño

### 1. Service Layer Pattern

**Dónde**: `api/services.py`, `api/analytics/services.py`

**Por qué**: Separar lógica de negocio de vistas

**Ejemplo**:
```python
# services.py
def pay_installment(installment_id, amount, payment_method):
    """Lógica compleja de pago"""
    # Validaciones
    # Cálculos
    # Transacciones
    return result

# views.py
@api_view(['POST'])
def pay_installment_view(request):
    """Vista simple delegando a servicio"""
    result = pay_installment(
        request.data['installment_id'],
        request.data['amount'],
        request.data['payment_method']
    )
    return Response(result)
```

### 2. Signal Pattern

**Dónde**: `api/signals.py`

**Por qué**: Desacoplamiento de efectos secundarios

**Ejemplo**:
```python
@receiver(post_save, sender=Purchase)
def send_purchase_notification(sender, instance, created, **kwargs):
    if created:
        send_email_task.delay(
            email=instance.user.email,
            template='purchase_confirmed',
            context={'purchase': instance}
        )
```

### 3. Manager Pattern

**Dónde**: Modelos con managers personalizados

**Por qué**: Encapsular queries complejas

**Ejemplo**:
```python
class InstallmentManager(models.Manager):
    def overdue(self):
        return self.filter(
            state=Installment.State.PENDING,
            due_date__lt=timezone.now().date()
        )
```

### 4. Factory Pattern

**Dónde**: Tests con Factory Boy

**Por qué**: Generación consistente de datos de prueba

**Ejemplo**:
```python
class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product
    
    name = factory.Faker('product_name')
    price = factory.Faker('pydecimal', left_digits=4, right_digits=2)
```

### 5. Strategy Pattern

**Dónde**: Sistema de reportes

**Por qué**: Diferentes algoritmos de generación según tipo

**Ejemplo**:
```python
REPORT_STRATEGIES = {
    'sales_summary': generate_sales_summary_report,
    'top_products': generate_top_products_report,
    # ... más estrategias
}

def generate_report(report_type, params):
    strategy = REPORT_STRATEGIES[report_type]
    return strategy(params)
```

### 6. Singleton Pattern

**Dónde**: `CacheManager`

**Por qué**: Una sola instancia para gestión de cache

**Ejemplo**:
```python
class CacheManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

---

## Decisiones Técnicas

### ¿Por qué Django + DRF?

**✅ Ventajas**:
- ORM robusto y maduro
- Admin panel incluido
- Gran ecosistema de paquetes
- Seguridad por defecto (CSRF, XSS, SQL Injection)
- Comunidad activa

**📚 Referencia**: [Django Documentation](https://docs.djangoproject.com/)

### ¿Por qué MySQL?

**✅ Ventajas**:
- ACID completo
- Buen rendimiento en reads
- Soporte de transacciones
- Compatible con hosting compartido
- Herramientas de administración maduras

**Alternativa evaluada**: PostgreSQL (ventaja: mejor JSON support)

### ¿Por qué Redis?

**✅ Ventajas**:
- Performance extrema (in-memory)
- TTL automático
- Patterns para invalidación
- Doble función: cache + message broker
- Fallback a LocMem sin cambios de código

**📚 Referencia**: [Redis Documentation](https://redis.io/documentation)

### ¿Por qué Celery?

**✅ Ventajas**:
- Procesamiento asíncrono robusto
- Beat scheduler incluido
- Retry automático
- Monitoreo con Flower
- Integración perfecta con Django

**📚 Referencia**: [Celery Documentation](https://docs.celeryproject.org/)

### ¿Por qué JWT?

**✅ Ventajas**:
- Stateless (no sesiones en servidor)
- Escalable horizontalmente
- Standard de industria
- Refresh tokens incluidos
- Compatible con móviles

**📚 Referencia**: [JWT.io](https://jwt.io/)

### ¿Por qué Docker?

**✅ Ventajas**:
- Entorno reproducible
- Fácil setup para desarrolladores
- CI/CD friendly
- Aislamiento de dependencias
- Deployment consistente

---

## Próximos Pasos

Para profundizar en áreas específicas:

- **Cache**: Ver [Sistema de Cache](CACHE.md)
- **Reportes**: Ver [Analytics](ANALYTICS.md)
- **API**: Ver [API Standards](API_STANDARDS.md)
- **Testing**: Ver [Testing Guide](TESTING.md)

---

**📚 Volver a**: [README principal](../README.md)
