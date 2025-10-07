from django.db import models


def get_total_stock(qs):
    stock_data = qs.aggregate(total=models.Sum("quantity"))
    total = stock_data["total"] or 0
    return total
