"""
Imports centralizados y reutilizables para vistas Django REST Framework.

Este módulo centraliza los imports más comunes que se repiten en múltiples
archivos views.py del proyecto, siguiendo el principio DRY.

En lugar de repetir los mismos imports en cada archivo, los módulos pueden
importar desde aquí los conjuntos de imports más utilizados.

Uso:
    # En lugar de repetir imports en cada views.py:
    # from rest_framework import viewsets, status
    # from rest_framework.response import Response
    # from rest_framework.permissions import IsAuthenticated, IsAdminUser
    # ...
    
    # Usar:
    from api.common_imports import *
    # o imports específicos:
    from api.common_imports import DRF_VIEWSET_IMPORTS, DRF_RESPONSE_IMPORTS
"""

# Imports básicos de DRF para ViewSets
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.decorators import api_view, permission_classes, authentication_classes

# Imports para documentación Swagger
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

# Imports de Django comunes
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone

# Imports para serializers
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

# Logging
import logging

# Constantes para conjuntos de imports organizados
DRF_VIEWSET_IMPORTS = [
    'viewsets', 'status', 'Response', 'IsAuthenticated',
    'IsAdminUser', 'AllowAny'
]

DRF_API_VIEW_IMPORTS = [
    'api_view', 'permission_classes', 'authentication_classes',
    'Response', 'status'
]

DRF_SWAGGER_IMPORTS = [
    'swagger_auto_schema', 'openapi', 'extend_schema',
    'OpenApiParameter', 'OpenApiTypes'
]

DRF_SERIALIZER_IMPORTS = [
    'serializers', 'ValidationError'
]

DJANGO_COMMON_IMPORTS = [
    'get_object_or_404', 'transaction', 'timezone'
]

# Re-exportar para facilitar el uso
__all__ = [
    # DRF ViewSets
    'viewsets', 'status', 'Response',
    'IsAuthenticated', 'IsAdminUser', 'AllowAny',
    'api_view', 'permission_classes', 'authentication_classes',

    # Swagger
    'swagger_auto_schema', 'openapi', 'extend_schema',
    'OpenApiParameter', 'OpenApiTypes',

    # Django
    'get_object_or_404', 'transaction', 'timezone',

    # Serializers
    'serializers', 'ValidationError',

    # Logging
    'logging',

    # Constantes
    'DRF_VIEWSET_IMPORTS', 'DRF_API_VIEW_IMPORTS',
    'DRF_SWAGGER_IMPORTS', 'DRF_SERIALIZER_IMPORTS',
    'DJANGO_COMMON_IMPORTS'
]
