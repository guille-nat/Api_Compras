import pytest


@pytest.mark.django_db
def test_inventory_record_out_serializer_fields():
    from api.inventories.serializers import InventoryRecordOutSerializer
    from api.inventories.models import InventoryRecord
    from api.products.models import Product
    from api.storage_location.models import StorageLocation

    p = Product.objects.create(product_code='PX', name='Prod X')
    loc = StorageLocation.objects.create(name='L1')

    rec = InventoryRecord.objects.create(product=p, location=loc, quantity=7)

    ser = InventoryRecordOutSerializer(rec)
    data = ser.data

    assert data['id'] == rec.id
    assert data['product'] == rec.product_id
    assert data['location'] == rec.location_id
    assert data['quantity'] == rec.quantity
