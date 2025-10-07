#!/usr/bin/env python3
"""
Test independiente para verificar la función convert_numpy_types
"""

import sys
import os

# Agregar el directorio del proyecto al path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

try:
    import numpy as np
    import pandas as pd
    from decimal import Decimal

    def convert_numpy_types(obj):
        """
        Convierte recursivamente tipos numpy a tipos nativos de Python para serialización JSON.

        Args:
            obj: Objeto que puede contener tipos numpy (dict, list, numpy types, etc.)

        Returns:
            Objeto con tipos nativos de Python
        """
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(convert_numpy_types(item) for item in obj)
        elif isinstance(obj, pd.Series):
            return obj.astype(object).tolist()
        elif isinstance(obj, Decimal):
            return float(obj)
        else:
            return obj

    # Test de la función convert_numpy_types
    print("=== Test de conversión de tipos numpy ===")

    test_data = {
        'numpy_int': np.int64(123),
        'numpy_float': np.float64(456.78),
        'regular_int': 789,
        'regular_string': 'test',
        'list_with_numpy': [np.int64(1), np.float64(2.5), 3],
        'decimal_value': Decimal('99.99'),
        'nested_dict': {
            'inner_numpy': np.int32(42),
            'inner_list': [np.float32(1.1), np.int8(2)]
        }
    }

    converted = convert_numpy_types(test_data)

    print('Conversión exitosa!')
    print('Datos originales:', test_data)
    print('Datos convertidos:', converted)
    print('Tipos convertidos:', {
          k: type(v).__name__ for k, v in converted.items()})

    # Verificar que puede ser serializado a JSON
    import json
    json_string = json.dumps(converted, indent=2)
    print('Serialización JSON exitosa!')
    print('JSON resultante:', json_string)

    print("\n=== Test de DataFrame a dict ===")

    # Simular el caso del DataFrame que causa el problema
    df_data = {
        'product__name': ['Producto A', 'Producto B', 'Producto C'],
        'total_quantity_sold': [np.int64(100), np.int64(75), np.int64(50)],
        'total_revenue': [Decimal('1000.50'), Decimal('750.25'), Decimal('500.00')]
    }

    df = pd.DataFrame(df_data)

    # Convertir a dict como lo hace la función original
    original_dict = df.to_dict(orient='records')
    print('Dict original (puede causar problema):', original_dict)
    print('Tipos originales:', {
          k: type(v).__name__ for item in original_dict for k, v in item.items()})

    # Aplicar conversión
    converted_dict = convert_numpy_types(original_dict)
    print('Dict convertido:', converted_dict)
    print('Tipos convertidos:', {
          k: type(v).__name__ for item in converted_dict for k, v in item.items()})

    # Verificar serialización
    json_string = json.dumps(converted_dict, indent=2)
    print('Serialización JSON del DataFrame exitosa!')

    print("\n🎉 Todos los tests pasaron correctamente!")

except Exception as e:
    print(f"Error en el test: {e}")
    import traceback
    traceback.print_exc()
