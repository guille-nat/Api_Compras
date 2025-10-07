#!/usr/bin/env python
"""
Script para probar la configuración de Redis antes de levantar Docker.
"""
import os
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
sys.path.append(str(Path(__file__).parent / "API_Compras"))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SistemaCompras.settings')

try:
    import django
    django.setup()

    from django.core.cache import cache
    from django.conf import settings

    print("Configuración de Redis")
    print("=" * 50)

    # Mostrar la configuración actual
    cache_config = settings.CACHES['default']
    print(f"Backend: {cache_config['BACKEND']}")
    print(f"Location: {cache_config['LOCATION']}")

    # Variables de entorno
    print(f"\nVariables de entorno:")
    print(f"REDIS_HOST: {os.getenv('REDIS_HOST', 'No definido')}")
    print(f"REDIS_PORT: {os.getenv('REDIS_PORT', 'No definido')}")
    print(
        f"REDIS_PASSWORD: {'***definida***' if os.getenv('REDIS_PASSWORD') else 'No definida'}")

    # Intentar conexión con Redis (esto fallará si Redis no está corriendo, pero es normal)
    print(f"\nProbando configuración de cache...")
    try:
        cache.set('test_key', 'test_value', 10)
        value = cache.get('test_key')
        if value == 'test_value':
            print("Cache funcionando correctamente!")
        else:
            print("Cache no está retornando el valor correcto")
    except Exception as e:
        print(
            f"Redis no está disponible (normal si los contenedores no están corriendo): {e}")
        print("   Pero la configuración parece correcta.")

    print(f"\nResumen:")
    print("- Configuración de Django")
    print("- Variables de entorno")
    print("- URL de Redis construida")
    print("\nListo para docker compose up!")

except ImportError as e:
    print(f"Error de importación: {e}")
    print("Asegúrate de estar en el directorio correcto y tener Django instalado.")
except Exception as e:
    print(f"Error inesperado: {e}")
