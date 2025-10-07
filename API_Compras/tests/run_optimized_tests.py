#!/usr/bin/env python
"""
Script para ejecutar tests optimizados y medir mejoras.
"""
import os
import sys
import time
import subprocess


def run_tests():
    """Ejecuta tests con las optimizaciones implementadas."""
    print("Ejecutando tests optimizados...")
    print("=" * 60)

    start_time = time.time()

    # Cambiar al directorio del proyecto
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Ejecutar pytest con las nuevas configuraciones
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            '-v',  # verbose para ver progreso
            '--tb=short',  # traceback corto
            '--maxfail=3',  # parar después de 3 fallos
        ], capture_output=True, text=True)

        end_time = time.time()
        execution_time = end_time - start_time

        print("RESULTADOS:")
        print(f"Tiempo de ejecución: {execution_time:.2f}s")
        print(
            f"Resultado: {'ÉXITO' if result.returncode == 0 else 'FALLÓ'}")

        # Mostrar salida de pytest
        if result.stdout:
            print("\nOUTPUT:")
            print(result.stdout)

        if result.stderr:
            print("\nWARNINGS/ERRORS:")
            print(result.stderr)

        # Analizar resultados
        if "passed" in result.stdout:
            lines = result.stdout.split('\n')
            for line in lines:
                if "passed" in line and ("skipped" in line or "warning" in line):
                    print(f"Estadísticas: {line.strip()}")
                    break

        print("=" * 60)

        if execution_time < 30:
            print("Excelente! Tests completados en menos de 30 segundos")
        elif execution_time < 40:
            print("Buena mejora! Tests completados en menos de 40 segundos")
        else:
            print("Tiempo aún alto, podrían necesitarse más optimizaciones")

        return result.returncode == 0

    except Exception as e:
        print(f"Error ejecutando tests: {e}")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
