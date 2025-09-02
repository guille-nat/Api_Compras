from django.db import models


def get_total_stock(qs):
    """
    Calcula el stock total (suma de cantidades) a partir de un QuerySet de registros
    de inventario (`InventoryRecord`).

    El QuerySet puede estar filtrado por producto, ubicación, lote o fecha de vencimiento,
    según la necesidad. Se utiliza `aggregate(Sum("quantity"))` y, en caso de no haber
    resultados o que la suma sea `None`, retorna 0.

    Args:
        qs (QuerySet[InventoryRecord]): Conjunto de registros de inventario sobre el que
            se desea calcular el stock total. Puede incluir filtros previos (por producto,
            ubicación, lote, etc.).

    Returns:
        int: Cantidad total de stock disponible en los registros del QuerySet. Siempre un
        número entero ≥ 0.

    Ejemplos:
        >>> qs = InventoryRecord.objects.filter(product=prod, location=loc)
        >>> total = calc_total_stock_by(qs)
        >>> print(total)
        150
    """
    stock_data = qs.aggregate(total=models.Sum("quantity"))
    total = stock_data["total"] or 0
    return total
