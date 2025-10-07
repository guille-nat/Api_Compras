import pytest


@pytest.mark.django_db
def test_list_inventory_records_and_movements():
    from api.inventories.selectors import list_inventory_records, list_inventory_movements
    from api.inventories.models import InventoryRecord, InventoryMovement
    from api.products.models import Product
    from api.storage_location.models import StorageLocation

    p = Product.objects.create(product_code='P1', name='Prod 1')
    loc = StorageLocation.objects.create(name='Loc1')

    InventoryRecord.objects.create(
        product=p, location=loc, quantity=10, batch_code='b1')
    InventoryRecord.objects.create(
        product=p, location=loc, quantity=5, batch_code='b2')

    qs = list_inventory_records()
    assert qs.count() >= 2

    im = InventoryMovement.objects.create(product=p, quantity=3, reason=InventoryMovement.Reason.ADJUSTMENT,
                                          description='', reference_type=InventoryMovement.RefType.MANUAL)
    mqs = list_inventory_movements()
    assert mqs.count() >= 1
