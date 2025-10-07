"""
Configuración global de fixtures para los tests del proyecto SistemaCompra.

Este módulo contiene fixtures que pueden ser utilizadas por todos los tests
del proyecto, incluyendo usuarios de prueba y configuraciones comunes.
"""
import os
import pytest
from django import setup
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta

# Configurar entorno para tests
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SistemaCompras.test_settings')

# Configurar Django si no está configurado
if not settings.configured:
    setup()

User = get_user_model()


@pytest.fixture
def user(db):
    """
    Fixture que crea un usuario de prueba básico.

    Returns:
        CustomUser: Usuario de prueba con datos estándar.
    """
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123"
    )


@pytest.fixture
def admin_user(db):
    """
    Fixture que crea un usuario administrador de prueba.

    Returns:
        CustomUser: Usuario administrador para tests que requieren permisos especiales.
    """
    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpass123"
    )


@pytest.fixture
def multiple_users(db):
    """
    Fixture que crea múltiples usuarios de prueba.

    Returns:
        list[CustomUser]: Lista de usuarios para tests que requieren múltiples usuarios.
    """
    users = []
    for i in range(3):
        user = User.objects.create_user(
            username=f"user{i}",
            email=f"user{i}@example.com",
            password=f"userpass{i}123"
        )
        users.append(user)
    return users


@pytest.fixture
def current_date():
    """
    Fixture que proporciona la fecha actual.

    Returns:
        date: Fecha actual para tests que necesitan fechas consistentes.
    """
    return date.today()


@pytest.fixture
def future_date():
    """
    Fixture que proporciona una fecha futura (30 días).

    Returns:
        date: Fecha futura para tests de vencimientos, etc.
    """
    return date.today() + timedelta(days=30)


@pytest.fixture
def past_date():
    """
    Fixture que proporciona una fecha pasada (30 días atrás).

    Returns:
        date: Fecha pasada para tests de vencimientos, auditoría, etc.
    """
    return date.today() - timedelta(days=30)


@pytest.fixture
def current_datetime():
    """
    Fixture que proporciona la fecha y hora actual.

    Returns:
        datetime: Datetime actual para tests que necesitan timestamps consistentes.
    """
    return timezone.now()


@pytest.fixture
def sample_decimal():
    """
    Fixture que proporciona un valor decimal de ejemplo.

    Returns:
        Decimal: Valor decimal para tests financieros.
    """
    return Decimal('1500.75')
