import pytest


@pytest.mark.django_db
def test_get_total_stock_aggregation():
    from api.inventories.utils import get_total_stock
    from api.inventories.models import InventoryRecord
    from api.products.models import Product
    from api.storage_location.models import StorageLocation

    p = Product.objects.create(product_code='STK', name='StockProd')
    loc = StorageLocation.objects.create(name='StockLoc')

    InventoryRecord.objects.create(
        product=p, location=loc, quantity=2, batch_code='u1')
    InventoryRecord.objects.create(
        product=p, location=loc, quantity=3, batch_code='u2')

    qs = InventoryRecord.objects.filter(product=p)
    total = get_total_stock(qs)
    assert total == 5


@pytest.mark.django_db
def test_purchase_entry_and_exit_sale_views(monkeypatch):
    from rest_framework.test import APIRequestFactory, force_authenticate
    from django.contrib.auth import get_user_model
    from api.inventories import views

    User = get_user_model()
    admin = User.objects.create_user(username='invadmin', password='pw',
                                     email='invadmin@example.test', is_staff=True, is_superuser=True)

    from api.products.models import Product
    from api.storage_location.models import StorageLocation

    product = Product.objects.create(product_code='TV100', name='TV')
    location = StorageLocation.objects.create(name='Main')

    factory = APIRequestFactory()

    # patch services.purchase_entry_inventory
    import uuid

    def fake_purchase(**kwargs):
        from api.inventories.models import InventoryRecord
        inv = InventoryRecord.objects.create(
            product=product, location=location, quantity=1, batch_code=str(uuid.uuid4())
        )
        return {
            "success": True,
            "message": "ok",
            "data": {
                "inventory": inv,
                "quantity_added": 1,
                "location": location.id,
                "product": product.id,
            }
        }

    # patch the service function where the view looks it up
    monkeypatch.setattr(
        'api.inventories.views.services.purchase_entry_inventory', fake_purchase)

    req = factory.post('/api/inventories/purchase',
                       {'product_id': product.id, 'quantity': 1, 'location_id': location.id}, format='json')
    force_authenticate(req, user=admin)
    resp = views.purchase_entry(req)
    resp.render()
    assert resp.status_code == 201

    # patch services.exit_sale_inventory
    def fake_exit(**kwargs):
        from api.inventories.models import InventoryRecord
        inv = InventoryRecord.objects.create(
            product=product, location=location, quantity=0, batch_code=str(uuid.uuid4())
        )
        return {
            "success": True,
            "message": "ok",
            "data": {
                "inventory": inv,
                "quantity_added": -1,
                "location": location.id,
                "product": product.id,
            }
        }

    monkeypatch.setattr(
        'api.inventories.views.services.exit_sale_inventory', fake_exit)

    req2 = factory.post('/api/inventories/exit', {
                        'product_id': product.id, 'quantity': 1, 'location_id': location.id}, format='json')
    force_authenticate(req2, user=admin)
    resp2 = views.exit_sale(req2)
    resp2.render()
    assert resp2.status_code == 201
