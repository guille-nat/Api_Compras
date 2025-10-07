#!/usr/bin/env python3
"""
Test simple de la función convert_numpy_types sin Django
"""

import numpy as np
import pandas as pd
from decimal import Decimal as _Decimal


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
    elif isinstance(obj, _Decimal):
        return float(obj)
    else:
        return obj


if __name__ == "__main__":
    print("Probando función convert_numpy_types...")

    # Test básico
    test_data = {
        'numpy_int': np.int64(123),
        'numpy_float': np.float64(456.78),
        'regular_int': 789,
        'regular_string': 'test',
        'list_with_numpy': [np.int64(1), np.float64(2.5), 3],
        'nested_dict': {
            'inner_numpy': np.int32(42),
            'inner_array': np.array([1, 2, 3])
        }
    }
    print("Datos originales:")
    for k, v in test_data.items():
        print(f"  {k}: {v} (tipo: {type(v)})")

    try:
        converted = convert_numpy_types(test_data)
        print("\nConversión exitosa!")
        print("Datos convertidos:")
        for k, v in converted.items():
            print(f"  {k}: {v} (tipo: {type(v)})")

        # Test de serialización JSON
        import json
        json_str = json.dumps(converted)
        print(f"\nSerialización JSON exitosa!")
        print(f"JSON: {json_str[:100]}...")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
