# 📊 Sistema de Reportes Asíncronos - Analytics

Documentación completa del sistema de Business Intelligence con generación asíncrona de reportes usando Celery.

## 📋 Tabla de Contenidos

- [Visión General](#visión-general)
- [Tipos de Reportes](#tipos-de-reportes)
- [Arquitectura Asíncrona](#arquitectura-asíncrona)
- [Uso de la API](#uso-de-la-api)
- [Formatos de Archivo](#formatos-de-archivo)
- [Configuración](#configuración)
- [Troubleshooting](#troubleshooting)

---

## Visión General

El sistema de Analytics permite generar reportes complejos sin bloquear el servidor mediante procesamiento asíncrono con **Celery**. Los reportes se generan en background y pueden descargarse cuando estén listos.

### Características Principales

✅ **Procesamiento Asíncrono**: No bloquea requests del cliente  
✅ **6 Tipos de Reportes**: Cobertura completa de Business Intelligence  
✅ **Multi-formato**: Excel, PNG, ZIP, JSON según necesidad  
✅ **Gráficos Profesionales**: Matplotlib integrado en Excel  
✅ **Almacenamiento Persistente**: Media storage de Django  
✅ **Autenticación**: Solo usuarios autenticados pueden generar reportes  
✅ **Auditoría**: Registro completo de reportes generados  

### Stack Técnico

- **Celery 5.5.3**: Task queue para procesamiento asíncrono
- **Redis**: Message broker y result backend
- **Pandas 2.3.2**: Análisis y transformación de datos
- **NumPy 2.2.6**: Cálculos numéricos
- **Matplotlib 3.10.6**: Generación de gráficos
- **OpenPyXL 3.1.5**: Creación de archivos Excel con gráficos embebidos

---

## Tipos de Reportes

### 1. 📦 Rotación de Productos (`product_rotation`)

**Descripción**: Analiza el stock actual de productos por ubicación de almacenamiento.

**Parámetros**:
- `start_date` *(opcional)*: Fecha inicio filtro
- `end_date` *(opcional)*: Fecha fin filtro

**Salida**: 
- **Archivo**: Excel (.xlsx)
- **Contenido**: Tabla con columnas: Producto, Ubicación, Stock, Última actualización

**Caso de uso**: Planificación de inventario, identificación de productos sin rotación.

**Ejemplo de datos**:
```
| Producto      | Ubicación  | Stock | Última Actualización |
|---------------|-----------|-------|---------------------|
| Laptop Dell   | Depósito A | 45   | 2024-01-15          |
| Mouse Logitech| Depósito B | 120  | 2024-01-14          |
```

---

### 2. 📊 Movimientos de Inventario (`movements`)

**Descripción**: Detalla todos los movimientos de entrada y salida de inventario.

**Parámetros**:
- `start_date`: Fecha inicio (requerido)
- `end_date`: Fecha fin (requerido)

**Salida**: 
- **Archivo**: Excel (.xlsx) o PNG (.png) si incluye gráfico
- **Contenido**: Movimientos con tipo (IN/OUT/TRANSFER), cantidad, fecha, responsable

**Caso de uso**: Auditoría de inventario, análisis de flujo de mercancía.

**Tipos de movimiento**:
- `IN`: Entrada de inventario
- `OUT`: Salida de inventario
- `TRANSFER`: Transferencia entre ubicaciones

---

### 3. 💰 Resumen de Ventas (`sales_summary`)

**Descripción**: Análisis completo de ventas con comparativas temporales y gráficos.

**Parámetros**:
- `start_date`: Fecha inicio (requerido)
- `end_date`: Fecha fin (requerido)

**Salida**: 
- **Archivo**: Excel (.xlsx) con **2 gráficos embebidos**
- **Gráfico 1**: Ingresos totales por período
- **Gráfico 2**: Comparativa de ventas vs período anterior

**Contenido del Excel**:
1. **Hoja "Resumen"**: Totales, promedios, métricas clave
2. **Hoja "Gráficos"**: Visualizaciones embebidas
3. **Hoja "Detalle"**: Ventas individuales

**Caso de uso**: Reportes gerenciales, análisis de tendencias, proyecciones.

**Ejemplo de métricas**:
```
- Total Ventas: $125,450.00
- Promedio Diario: $4,182.00
- Crecimiento vs Anterior: +15.3%
- Producto Top: Laptop Dell (45 unidades)
```

---

### 4. 🏆 Top Productos (`top_products`)

**Descripción**: Ranking de productos más vendidos en un período.

**Parámetros**:
- `start_date`: Fecha inicio (requerido)
- `end_date`: Fecha fin (requerido)
- `limit`: Cantidad de productos (default: 10, máx: 100)

**Salida**: 
- **Archivo**: Excel (.xlsx) o PNG (.png) con gráfico de barras
- **Contenido**: Ranking con unidades vendidas, ingresos generados, margen

**Caso de uso**: Estrategia de ventas, gestión de stock prioritario.

**Ejemplo de salida**:
```
| Posición | Producto       | Unidades | Ingresos    | Margen  |
|----------|----------------|----------|-------------|---------|
| 1        | Laptop Dell    | 145      | $87,000.00  | 22%     |
| 2        | iPhone 15      | 98       | $68,600.00  | 30%     |
| 3        | Auriculares BT | 320      | $16,000.00  | 40%     |
```

---

### 5. 💳 Métodos de Pago (`payment_methods`)

**Descripción**: Distribución de ventas por método de pago.

**Parámetros**:
- `start_date`: Fecha inicio (requerido)
- `end_date`: Fecha fin (requerido)

**Salida**: 
- **Archivo**: ZIP conteniendo:
  - `payment_methods.xlsx`: Tabla detallada
  - `payment_distribution.png`: Gráfico de torta (pie chart)

**Contenido**:
- Cantidad de transacciones por método
- Monto total por método
- Porcentaje de uso
- Promedio de ticket

**Caso de uso**: Análisis de preferencias de pago, optimización de comisiones.

**Métodos soportados**:
- `CASH`: Efectivo
- `CARD`: Tarjeta crédito/débito
- `TRANSFER`: Transferencia bancaria
- `OTHER`: Otros métodos

---

### 6. ⚠️ Cuotas Vencidas (`overdue_installments`)

**Descripción**: Reporte de cuotas impagas vencidas con cálculo de mora.

**Parámetros**:
- `start_date` *(opcional)*: Fecha inicio filtro
- `end_date` *(opcional)*: Fecha fin filtro

**Salida**: 
- **Archivo**: Excel (.xlsx)
- **Contenido**: Cuotas vencidas con días de atraso, mora calculada, contacto del cliente

**Caso de uso**: Gestión de cobranzas, análisis de morosidad.

**Ejemplo de salida**:
```
| Cliente         | Cuota | Monto Original | Mora     | Total Adeudado | Días Atraso | Contacto          |
|-----------------|-------|----------------|----------|----------------|-------------|-------------------|
| Juan Pérez      | 3/12  | $500.00       | $75.00   | $575.00        | 15          | juan@email.com    |
| María González  | 2/6   | $1,200.00     | $240.00  | $1,440.00      | 30          | maria@email.com   |
```

**Cálculo de mora**:
- **Tasa diaria**: Configurable en settings (default: 0.5% diario)
- **Fórmula**: `mora = monto_original * tasa_diaria * días_atraso`

---

## Arquitectura Asíncrona

### Flujo Completo de Generación

```
┌─────────┐                 ┌─────────┐                ┌────────────┐
│ Cliente │                 │ Django  │                │   Celery   │
└────┬────┘                 └────┬────┘                └─────┬──────┘
     │                           │                           │
     │ 1. POST /reports/sales/create/                       │
     ├──────────────────────────▶│                           │
     │                           │                           │
     │                           │ 2. Validar autenticación  │
     │                           │    y parámetros           │
     │                           │                           │
     │                           │ 3. Crear Report (status=PENDING)
     │                           │                           │
     │                           │ 4. Encolar tarea Celery   │
     │                           ├──────────────────────────▶│
     │                           │                           │
     │ 5. Response inmediata     │                           │
     │    {"task_id": "abc123"}  │                           │
     │◀──────────────────────────┤                           │
     │                           │                           │
     │                           │                           │ 6. Procesar
     │                           │                           │    en background
     │                           │                           │
     │                           │                           │ 7. Generar Excel
     │                           │                           │    con gráficos
     │                           │                           │
     │                           │ 8. Actualizar Report      │
     │                           │    (status=COMPLETED)     │
     │                           │◀──────────────────────────┤
     │                           │                           │
     │ 9. Consultar estado       │                           │
     │ GET /reports/status/{task_id}/                        │
     ├──────────────────────────▶│                           │
     │                           │                           │
     │ 10. Response con progreso │                           │
     │     {"status": "COMPLETED"}│                          │
     │◀──────────────────────────┤                           │
     │                           │                           │
     │ 11. Descargar archivo     │                           │
     │ GET /reports/{id}/download/                           │
     ├──────────────────────────▶│                           │
     │                           │                           │
     │ 12. Stream del archivo    │                           │
     │◀──────────────────────────┤                           │
     └───────────────────────────┘                           │
```

### Estados de un Reporte

```python
class ReportState:
    PENDING = 'pending'       # Encolado, esperando procesamiento
    PROCESSING = 'processing' # Celery worker ejecutando
    COMPLETED = 'completed'   # Generado exitosamente
    FAILED = 'failed'         # Error durante generación
```

---

## Uso de la API

### Autenticación

Todos los endpoints requieren autenticación JWT:

```bash
# 1. Obtener token
curl -X POST http://localhost:8000/api/v2/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Response:
# {
#   "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
#   "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
# }
```

### 1. Crear Reporte

**Endpoint**: `POST /api/v2/reports/{report_type}/create/`

**Report types disponibles**:
- `product_rotation`
- `movements`
- `sales`
- `top_products`
- `payment_methods`
- `overdue_installments`

**Ejemplo - Resumen de ventas**:

```bash
curl -X POST http://localhost:8000/api/v2/reports/sales/create/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  }'
```

**Response exitosa** (201 Created):
```json
{
  "message": "Report queued for processing",
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "report_id": 42,
  "status": "pending"
}
```

**Errores comunes** (400 Bad Request):
```json
{
  "errors": {
    "start_date": ["This field is required"],
    "end_date": ["Start date cannot be after end date"]
  }
}
```

### 2. Consultar Estado

**Endpoint**: `GET /api/v2/reports/status/{task_id}/`

```bash
curl -X GET http://localhost:8000/api/v2/reports/status/a1b2c3d4-e5f6-7890-abcd-ef1234567890/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response - En proceso**:
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "processing",
  "report_id": 42,
  "message": "Report is being generated"
}
```

**Response - Completado**:
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "report_id": 42,
  "file_url": "/api/v2/reports/42/download/",
  "message": "Report completed successfully"
}
```

**Response - Error**:
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "failed",
  "report_id": 42,
  "error": "Insufficient data for the selected period",
  "message": "Report generation failed"
}
```

### 3. Descargar Reporte

**Endpoint**: `GET /api/v2/reports/{report_id}/download/`

```bash
curl -X GET http://localhost:8000/api/v2/reports/42/download/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  --output sales_summary.xlsx
```

**Response**: 
- **Content-Type**: Automático según archivo (Excel/PNG/ZIP/JSON)
- **Content-Disposition**: `attachment; filename="sales_summary_2024-01-31.xlsx"`
- **Body**: Binary stream del archivo

### 4. Listar Reportes del Usuario

**Endpoint**: `GET /api/v2/reports/`

**Query parameters**:
- `report_type` *(opcional)*: Filtrar por tipo
- `state` *(opcional)*: Filtrar por estado
- `limit`: Paginación (default: 20)

```bash
curl -X GET "http://localhost:8000/api/v2/reports/?report_type=sales&state=completed" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response**:
```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 42,
      "report_type": "sales",
      "state": "completed",
      "created_at": "2024-01-15T10:30:00Z",
      "completed_at": "2024-01-15T10:35:22Z",
      "file_url": "/api/v2/reports/42/download/",
      "parameters": {
        "start_date": "2024-01-01",
        "end_date": "2024-01-31"
      }
    },
    // ... más reportes
  ]
}
```

---

## Formatos de Archivo

### Detección Automática

El sistema detecta automáticamente el tipo de archivo generado:

```python
# Orden de detección en tasks.py
if 'zip' in content_type or 'application/zip' in content_type:
    file_type = Report.FileType.ZIP
elif 'png' in content_type or 'image' in content_type:
    file_type = Report.FileType.PNG
elif 'excel' in content_type or 'spreadsheet' in content_type:
    file_type = Report.FileType.EXCEL
else:
    file_type = Report.FileType.EXCEL  # Default
```

### Matriz de Tipos por Reporte

| Reporte                | Formato Principal | Formato Alternativo | Notas                              |
|------------------------|-------------------|--------------------|------------------------------------|
| `product_rotation`     | Excel (.xlsx)     | -                  | Tabla simple                       |
| `movements`            | Excel (.xlsx)     | PNG (.png)         | PNG si incluye gráfico temporal    |
| `sales_summary`        | Excel (.xlsx)     | -                  | **SIEMPRE** con 2 gráficos embebidos |
| `top_products`         | Excel (.xlsx)     | PNG (.png)         | PNG con gráfico de barras          |
| `payment_methods`      | ZIP (.zip)        | -                  | Contiene Excel + PNG (pie chart)   |
| `overdue_installments` | Excel (.xlsx)     | -                  | Tabla con cálculos de mora         |

---

## Configuración

### Variables de Entorno

Configurar en `.env`:

```bash
# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Analytics
ANALYTICS_MAX_EXPORT_ROWS=10000      # Límite de filas en Excel
ANALYTICS_CHART_WIDTH=12             # Ancho de gráficos (inches)
ANALYTICS_CHART_HEIGHT=6             # Alto de gráficos (inches)
ANALYTICS_DEFAULT_TOP_LIMIT=10       # Top productos por defecto
ANALYTICS_MAX_TOP_LIMIT=100          # Máximo top productos

# Mora (cuotas vencidas)
INSTALLMENT_DAILY_PENALTY_RATE=0.005  # 0.5% diario
```

### Configuración de Celery

En `SistemaCompras/celery.py`:

```python
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Argentina/Buenos_Aires',
    enable_utc=True,
    task_track_started=True,  # Tracking de estado PROCESSING
    task_time_limit=1800,     # 30 minutos máximo por reporte
    task_soft_time_limit=1500, # Soft limit a 25 minutos
)
```

### Almacenamiento de Archivos

Configurado en `settings.py`:

```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Los reportes se guardan en:
# media/reports/{year}/{month}/{day}/report_{id}_{timestamp}.{ext}
```

---

## Troubleshooting

### Error: "Celery worker not available"

**Síntoma**: Reportes quedan en estado `PENDING` indefinidamente.

**Solución**:
```bash
# Verificar que Celery worker esté corriendo
docker-compose ps celery_worker

# Si no está corriendo
docker-compose up -d celery_worker

# Ver logs
docker-compose logs -f celery_worker
```

### Error: "Report generation timeout"

**Síntoma**: Reporte pasa a `FAILED` con mensaje de timeout.

**Causas posibles**:
- Rango de fechas muy amplio
- Demasiados datos para procesar

**Solución**:
```python
# Aumentar time limit en celery.py
app.conf.update(
    task_time_limit=3600,  # 1 hora
)

# O reducir rango de fechas en la solicitud
```

### Error: "File not found" al descargar

**Síntoma**: 404 al intentar descargar reporte completado.

**Solución**:
```bash
# Verificar permisos de media/
chmod -R 755 media/

# Verificar que el archivo existe
docker-compose exec backend ls -la media/reports/

# Verificar MEDIA_ROOT en settings.py
```

### Error: "Out of memory" generando reportes grandes

**Síntoma**: Celery worker se reinicia durante generación.

**Solución**:
```yaml
# docker-compose.yml - Aumentar memoria del worker
services:
  celery_worker:
    deploy:
      resources:
        limits:
          memory: 2G  # Aumentar de 1G a 2G
```

### Reportes lentos

**Diagnóstico**:
```python
# Habilitar logging detallado en tasks.py
logger.setLevel(logging.DEBUG)

# Ver queries SQL ejecutadas
# Agregar en task:
from django.db import connection
logger.debug(f"Queries: {len(connection.queries)}")
```

**Optimizaciones**:
- Agregar índices en fechas: `purchase_date`, `due_date`
- Usar `select_related()` / `prefetch_related()`
- Implementar cache para datos repetitivos

---

## Próximos Pasos

Para información complementaria:

- **Arquitectura General**: Ver [Architecture](ARCHITECTURE.md)
- **Configuración Docker**: Ver [Docker](DOCKER.md)
- **Testing de Reportes**: Ver [Testing](TESTING.md)
- **API Completa**: Ver [Swagger UI](http://localhost:8000/api/schema/swagger-ui/)

---

**📚 Volver a**: [README principal](../README.md)
