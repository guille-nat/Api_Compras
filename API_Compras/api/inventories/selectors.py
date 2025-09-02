from .models import InventoryMovement, InventoryRecord


def list_inventory_records():
    return InventoryRecord.objects.select_related(
        "product", "location", "created_by", "updated_by"
    ).order_by(
        "product__name", "location__name",
        "expiry_date__isnull", "batch_code__isnull",
        "expiry_date", "batch_code"
    )


def list_inventory_movements():
    return InventoryMovement.objects.select_related(
        "product", "from_location", "to_location"
    ).order_by("-occurred_at")


def select_inventory_record_by_product(product_id: int):
    return InventoryRecord.objects.select_related(
        "product", "location", "created_by", "updated_by"
    ).filter(product_id=product_id)


def select_inventory_record_by_record(record_id: int):
    return InventoryRecord.objects.select_related(
        "product", "location", "created_by", "updated_by"
    ).get(id=record_id)
