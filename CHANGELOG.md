# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-07

### Added

- **Gestión de productos e inventario**: Sistema completo para manejo de productos
- **Registro de compras**: Sistema de compras con detalles asociados
- **Manejo de cuotas y pagos**: Sistema de pagos con descuentos y recargos
- **Notificaciones automáticas**: Sistema de notificaciones para usuarios sobre compras y pagos
- **Autenticación JWT**: Implementación de autenticación con JSON Web Tokens bajo esquema Bearer
- **API RESTful**: Endpoints completos para todas las funcionalidades

### Technical Features

- Django 5.1.5 with Django REST Framework 3.15.2
- JWT Authentication with djangorestframework_simplejwt 5.4.0
- MySQL database support with mysqlclient 2.2.7
- API documentation with drf-yasg 1.21.8
- CORS support with django-cors-headers 4.6.0

### Architecture

- URIs en inglés y en plural
- Eliminación de la barra final en rutas
- Migraciones centralizadas en el root
- Modelo de usuario personalizado (CustomUser)
- Campos string guardados en minúsculas (excepto claves como product_code y payment_method)

### Applications

- **API Core**: Funcionalidades base y utilidades
- **Products**: Gestión de productos e inventario
- **Purchases**: Sistema de compras
- **Payments**: Sistema de pagos y cuotas
- **Users**: Gestión de usuarios con modelo personalizado

### Dependencies

- asgiref==3.8.1
- Django==5.1.5
- django-cors-headers==4.6.0
- djangorestframework==3.15.2
- djangorestframework_simplejwt==5.4.0
- drf-yasg==1.21.8
- inflection==0.5.1
- mysqlclient==2.2.7
- PyJWT==2.10.1
- python-dotenv==1.0.1
- Y otras dependencias de soporte