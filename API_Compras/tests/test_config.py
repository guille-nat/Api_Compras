#!/usr/bin/env python
"""
Script simple para probar configuración de pytest sin coverage.
"""
import os
import sys
import subprocess


def check_basic_pytest():
    """Prueba pytest sin coverage primero."""
    print("Probando pytest básico (sin coverage)...")

    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        # Probar pytest básico sin coverage
        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            'tests/test_permission_basic.py',
            '-v', '--tb=short', '--no-cov'
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Pytest básico funciona")
            print("Output:")
            print(result.stdout[-500:])  # Últimas 500 caracteres
            return True
        else:
            print("❌ Pytest básico falló:")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def check_coverage_config():
    """Prueba la configuración de coverage."""
    print("\nProbando configuración de coverage...")

    try:
        # Probar coverage directamente
        result = subprocess.run([
            sys.executable, '-m', 'coverage', '--help'
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Coverage instalado correctamente")

            # Probar que lee la configuración
            result = subprocess.run([
                sys.executable, '-c',
                'import coverage; c = coverage.Coverage(); print("Config OK")'
            ], capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ Configuración de coverage válida")
                return True
            else:
                print("❌ Error en configuración de coverage:")
                print(result.stderr)
                return False
        else:
            print("❌ Coverage no disponible")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("DIAGNÓSTICO DE CONFIGURACIÓN")
    print("=" * 40)

    basic_ok = check_basic_pytest()
    coverage_ok = check_coverage_config()

    print("\n" + "=" * 40)
    if basic_ok and coverage_ok:
        print("¡Todo funciona! Ahora puedes ejecutar pytest normalmente")
    elif basic_ok:
        print("Pytest funciona, pero hay problemas con coverage")
        print("Puedes ejecutar: pytest --no-cov")
    else:
        print("Problemas con pytest - revisar configuración")


if __name__ == "__main__":
    main()
