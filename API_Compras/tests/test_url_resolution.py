#!/usr/bin/env python
"""
Script simple para probar la resolución de URLs en Django.
"""
from django.conf import settings
from django.urls import resolve, reverse
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SistemaCompras.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()


def test_url_resolution():
    print("=== Probando resolución de URLs ===")

    # URLs a probar
    test_urls = [
        '/api/v2/admin/analytics/top-products/',
        '/api/v2/admin/analytics/top-products',
    ]

    for url in test_urls:
        try:
            resolved = resolve(url)
            print(
                f"✓ URL '{url}' resuelve a: {resolved.func.__name__} en {resolved.func.__module__}")
        except Exception as e:
            print(f"✗ Error resolviendo '{url}': {e}")

    # Verificar URLs disponibles
    print("\n=== URLs disponibles en URLconf ===")
    from django.urls import get_resolver
    resolver = get_resolver()

    def print_url_patterns(patterns, prefix=''):
        for pattern in patterns:
            if hasattr(pattern, 'url_patterns'):
                print_url_patterns(pattern.url_patterns,
                                   prefix + str(pattern.pattern))
            else:
                print(f"  {prefix}{pattern.pattern}")

    print_url_patterns(resolver.url_patterns)


if __name__ == '__main__':
    test_url_resolution()
