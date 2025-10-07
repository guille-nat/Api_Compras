# 🛒 Sistema de Compras - API REST

> **Sistema completo de gestión de compras, pagos en cuotas, inventario y analíticas empresariales con arquitectura moderna y alto rendimiento.**

[![Django](https://img.shields.io/badge/Django-5.1.5-green.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15.2-red.svg)](https://www.django-rest-framework.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![Redis](https://img.shields.io/badge/Redis-Cache-DC382D.svg)](https://redis.io/)
[![MySQL](https://img.shields.io/badge/MySQL-9.0-4479A1.svg)](https://www.mysql.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🌟 Características Principales

### 🚀 **Alto Rendimiento**


- **Cache Redis** con invalidación inteligente y métricas en tiempo real
- **Optimización de consultas** con `select_related` y `prefetch_related`
- **Paginación eficiente** para grandes volúmenes de datos
- **Arquitectura escalable** lista para microservicios


### 📊 **Business Intelligence**

- **Reportes asíncronos** con Celery para procesamiento en segundo plano
- **Gráficos profesionales** con Matplotlib integrados en Excel
- **Analíticas avanzadas**: rotación de productos, ventas, mora, inventario
- **Multi-formato**: Excel, PNG, ZIP, JSON


### 🔐 **Seguridad Empresarial**

- **Autenticación JWT** con tokens de acceso y refresco
- **Permisos granulares** por rol (Admin/Staff/User)
- **Validación robusta** de datos en todas las capas

- **Auditoría completa** de operaciones críticas

### 🧪 **Calidad de Código**

- **+300 tests automatizados** con pytest (coverage >85%)
- **Documentación OpenAPI 3.0** con Swagger UI y ReDoc

- **Clean Code** siguiendo principios SOLID
- **Type hints** y validación estricta

### 🐳 **DevOps Ready**

- **Docker Compose** con hot-reload para desarrollo
- **CI/CD friendly** con variables de entorno
- **Logs estructurados** para monitoreo
- **Healthchecks** en todos los servicios

---

## 📋 Tabla de Contenidos

- [Inicio Rápido](#-inicio-rápido)
- [Stack Tecnológico](#-stack-tecnológico)
- [Arquitectura](#️-arquitectura)
- [Documentación](#-documentación)
- [Desarrollo](#-desarrollo)
- [Testing](#-testing)
- [Contribuir](#-contribuir)
- [Licencia](#-licencia)

---

## 🚀 Inicio Rápido

### Prerequisitos

- Docker & Docker Compose
- Git
- 4GB RAM mínimo

### Instalación con Docker (Recomendado)

```bash
# 1. Clonar repositorio
git clone https://github.com/guille-nat/Api_Compras.git
cd Api_Compras

# 2. Configurar variables de entorno
cp API_Compras/.env.example API_Compras/.env
# Editar .env con tus configuraciones

# 3. Levantar servicios
docker-compose up -d --build

# 4. Verificar servicios
docker ps

# 5. Acceder a la aplicación
# API: http://localhost:8000/api/v2/
# Admin: http://localhost:8000/admin/
# Swagger: http://localhost:8000/api/v2/schema/swagger-ui/
# ReDoc: http://localhost:8000/api/v2/schema/redoc/
```

### Primeros Pasos

```bash
# Generar datos de prueba
docker-compose exec backend python manage.py generate_data

# Crear superusuario
docker-compose exec backend python manage.py createsuperuser

# Ver logs
docker-compose logs -f backend
```

**📖 Guía completa**: Ver [Documentación de Instalación](doc/INSTALLATION.md)


---

## 🛠️ Stack Tecnológico

### Backend


- **Django 5.1.5** - Framework web robusto y escalable
- **Django REST Framework 3.15.2** - API REST con todas las funcionalidades
- **Celery 5.5.3** - Procesamiento asíncrono de tareas
- **Redis 7** - Cache de alta velocidad y message broker


### Base de Datos

- **MySQL 9.0** - Base de datos relacional principal
- **django-redis 6.0.0** - Backend de cache optimizado


### Analíticas

- **Pandas 2.3.2** - Procesamiento de datos
- **NumPy 2.2.6** - Cálculos numéricos

- **Matplotlib 3.10.6** - Visualización de datos
- **OpenPyXL 3.1.5** - Generación de Excel

### Documentación

- **drf-spectacular 0.26.5** - OpenAPI 3.0 schema
- **drf-yasg 1.21.8** - Swagger UI mejorado

### Testing

- **Pytest 8.4.1** - Framework de testing moderno
- **Factory Boy 3.3.3** - Generación de datos de prueba
- **Coverage 6.2.1** - Análisis de cobertura

**📦 Dependencias completas**: Ver [requirements.txt](API_Compras/requirements.txt)

---

## 🏗️ Arquitectura

### Estructura del Proyecto

```
SistemaCompra/
├── API_Compras/          # Aplicación Django principal
│   ├── api/              # Apps modulares
│   │   ├── analytics/    # 📊 Reportes y BI
│   │   ├── cache/        # 🚀 Sistema de cache
│   │   ├── categories/   # 📂 Categorías
│   │   ├── inventories/  # 📦 Inventario
│   │   ├── payments/     # 💳 Pagos y cuotas
│   │   ├── products/     # 🛍️ Productos
│   │   ├── promotions/   # 🎁 Promociones
│   │   ├── purchases/    # 🛒 Compras
│   │   ├── storage_location/  # 🏢 Ubicaciones
│   │   └── users/        # 👥 Usuarios

│   ├── SistemaCompras/   # Configuración Django
│   └── manage.py
├── doc/                  # 📚 Documentación técnica
├── redis/                # ⚙️ Configuración Redis
└── docker-compose.yml    # 🐳 Orquestación
```

### Módulos Principales


#### 📊 Analytics (Reportes Asíncronos)

- Rotación de productos por ubicación
- Movimientos de inventario (entrada/salida)
- Resumen de ventas con gráficos

- Productos más vendidos (Top N)
- Análisis de métodos de pago
- Reporte de cuotas vencidas con mora

#### 🚀 Cache System


- Invalidación inteligente por patrones
- Métricas de rendimiento en tiempo real
- Dashboard administrativo
- Precalentamiento automático

#### 💳 Payments (Sistema de Cuotas)

- Cálculo automático de cuotas
- Gestión de mora y recargos
- Pagos parciales y totales
- Auditoría completa de cambios

#### 🛍️ Products & Inventory

- Control de stock por ubicación
- Movimientos con trazabilidad
- Snapshots históricos
- Alertas de stock bajo

**🏗️ Diagrama completo**: Ver [Arquitectura Detallada](doc/ARCHITECTURE.md)

---

## 📚 Documentación

### Guías Principales

| Documento | Descripción |
|-----------|-----<http://localhost:8000/api/v2/schema/swagger-ui/>
| [📥 Instala<http://localhost:8000/api/v2/schema/redoc/> de instalación local y Docker |
| [🏗️ Arquitectura](d<http://localhost:8000/api/v2/schema/>tema y decisiones técnicas |
| [🚀 Cache Redis](doc/CACHE.md) | Sistema de cache y optimización |
| [📊 Analytics](doc/ANALYTICS.md) | Reportes asíncronos con Celery |
| [🔐 Autenticación](doc/AUTHENTICATION.md) | JWT, permisos y seguridad |
| [🐳 Docker](doc/DOCKER.md) | Configuración y troubleshooting |
| [⚙️ Variables de Entorno](doc/ENVIRONMENT.md) | Configuración completa |
| [🔧 API Standards](doc/API_STANDARDS.md) | Estándares de respuestas |
| [🔕 Signals Control](doc/SIGNALS.md) | Control de notificaciones |
| [🧪 Testing](doc/TESTING.md) | Guía de testing y cobertura |

### API Interactiva

- **Swagger UI**: <http://localhost:8000/api/v2/schema/swagger-ui/>
- **ReDoc**: <http://localhost:8000/api/v2/schema/redoc/>
- **OpenAPI Schema**: <http://localhost:8000/api/v2/schema/>

---

## 💻 Desarrollo

### Setup Local

```bash
# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate    # Windows

# Instalar dependencias
cd API_Compras
pip install -r requirements.txt

# Configurar base de datos
cp .env.example .env
# Editar .env con tus configuraciones

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Iniciar servidor de desarrollo
python manage.py runserver
```

### Comandos Útiles

```bash
# Generar datos de prueba
python manage.py generate_data --products 500 --users 100

# Ver estadísticas de cache
python manage.py cache_admin stats

# Limpiar cache
python manage.py cache_admin clear

# Ejecutar tests
pytest

# Cobertura de tests
pytest --cov=api --cov-report=html

# Django shell mejorado
python manage.py shell_plus --ipython

# Ver tareas de Celery
celery -A SistemaCompras inspect active
```

**🔧 Más comandos**: Ver [Guía de Desarrollo](doc/DEVELOPMENT.md)

---

## 🧪 Testing

### Ejecutar Tests

```bash
# Todos los tests
pytest

# Tests específicos
pytest api/analytics/tests/
pytest api/payments/tests/test_installments.py

# Con cobertura
pytest --cov=api --cov-report=html
# Ver reporte: htmlcov/index.html

# Verbose con logs
pytest -vv -s
```

### Cobertura

```bash
# Reporte en terminal
pytest --cov=api

# Reporte HTML detallado
pytest --cov=api --cov-report=html

# Reporte XML (para CI/CD)
pytest --cov=api --cov-report=xml
```

**Objetivo**: Mantener cobertura >85%

**🧪 Guía completa**: Ver [Testing Guide](doc/TESTING.md)

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Por favor lee la [Guía de Contribución](CONTRIBUTING.md) antes de enviar un Pull Request.

### Proceso

1. Fork del proyecto
2. Crear rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

### Estándares de Código

- Seguir PEP 8
- Escribir docstrings en español
- Agregar tests para nuevas funcionalidades
- Mantener cobertura >85%
- Usar type hints cuando sea posible

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo [LICENSE](LICENSE) para más detalles.

---

## 👥 Autores

- **Guillermo Natali** - *Desarrollo principal* - [@guille-nat](https://github.com/guille-nat)

---<gutierrezfalopaalberto@gmail.com>

## 🙏 Agradecimientos

- Django y Django REST Framework communities
- Contribuidores de librerías open source
- Todos los que han aportado feedback y sugerencias

---

## 📞 Soporte

- **Issues**: [GitHub Issues](https://github.com/guille-nat/Api_Compras/issues)
- **Documentación**: [Wiki del Proyecto](https://github.com/guille-nat/Api_Compras/wiki)
- **Email**: <gutierrezfalopaalberto@gmail.com>

---

<p align="center">
  Hecho con ❤️ usando Django y DRF
</p>
