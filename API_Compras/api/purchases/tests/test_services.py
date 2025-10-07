import pytest
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model

from api.purchases import services as purchase_services
from api.purchases.models import Purchase, PurchaseDetail
from api.products.models import Product
from api.storage_location.models import StorageLocation
from api.categories.models import Category
from api.inventories.models import InventoryRecord


User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create(username='buyer', email='buyer@example.com')


@pytest.mark.django_db
def test_create_purchase_detail_happy(monkeypatch, user):
    # setup product, location and inventory
    product = Product.objects.create(
        product_code='P1', name='Prod1', unit_price=Decimal('10.00'))
    loc = StorageLocation.objects.create(
        name='L1', street='S', street_number='1', state='S', city='C', country='Ct')
    # inventory with sufficient stock
    ir = InventoryRecord.objects.create(
        product=product, location=loc, quantity=20, batch_code='B1')

    # create a purchase to attach detail
    purchase = Purchase.objects.create(user_id=user.pk, purchase_date=timezone.now(), total_amount=Decimal(
        '0.00'), total_installments_count=1, status=Purchase.Status.OPEN, created_by=user)

    # Patch exit_sale_inventory to simulate successful stock decrement without side-effects
    def fake_exit_sale_inventory(*args, **kwargs):
        return {"success": True}

    monkeypatch.setattr(
        'api.purchases.services.exit_sale_inventory', fake_exit_sale_inventory)

    res = purchase_services.create_purchase_detail(
        purchase_id=purchase.pk, product=product, quantity=2, location_ids=[loc.pk])
    assert res['success'] is True
    data = res['data']
    assert data['quantity'] == 2
    assert data['unit_price_at_purchase'] == product.unit_price
    assert data['subtotal'] == (
        product.unit_price * 2).quantize(Decimal('0.01'))


@pytest.mark.django_db
def test_create_purchase_detail_insufficient_stock(monkeypatch, user):
    product = Product.objects.create(
        product_code='P2', name='Prod2', unit_price=Decimal('5.00'))
    loc = StorageLocation.objects.create(
        name='L2', street='S', street_number='2', state='S', city='C', country='Ct')
    InventoryRecord.objects.create(
        product=product, location=loc, quantity=1, batch_code='B2')

    purchase = Purchase.objects.create(user_id=user.pk, purchase_date=timezone.now(), total_amount=Decimal(
        '0.00'), total_installments_count=1, status=Purchase.Status.OPEN, created_by=user)

    monkeypatch.setattr(
        'api.purchases.services.exit_sale_inventory', lambda *a, **k: {"success": True})

    with pytest.raises(ValueError):
        purchase_services.create_purchase_detail(
            purchase_id=purchase.pk, product=product, quantity=5, location_ids=[loc.pk])


@pytest.mark.django_db
def test_create_purchase_happy(monkeypatch, user):
    # create two products and monkeypatch create_purchase_detail to avoid inventory complexity
    p1 = Product.objects.create(
        product_code='PX1', name='PX1', unit_price=Decimal('3.00'))
    p2 = Product.objects.create(
        product_code='PX2', name='PX2', unit_price=Decimal('4.00'))
    # stub create_purchase_detail to return consistent detail dict

    def fake_create_purchase_detail(purchase_id, product, quantity, location_ids):
        subtotal = (product.unit_price * quantity).quantize(Decimal('0.01'))
        return {"success": True, "data": {"subtotal": subtotal}}

    monkeypatch.setattr(
        'api.purchases.services.create_purchase_detail', fake_create_purchase_detail)

    res = purchase_services.create_purchase(user_id=user.pk, installments_count=1, products_ids_quantity=[
                                            (p1.pk, 2), (p2.pk, 1)], location_ids=[1])
    assert res['success'] is True
    assert 'data' in res
    assert 'purchase' in res['data']
    assert res['data']['purchase']['total_amount'] == (
        p1.unit_price * 2 + p2.unit_price * 1).quantize(Decimal('0.01'))


@pytest.mark.django_db
def test_get_user_purchases_and_filters(user):
    # create a purchase and detail and assert get_user_purchases returns it
    p = Product.objects.create(
        product_code='GP1', name='GP1', unit_price=Decimal('2.50'))
    purchase = Purchase.objects.create(user_id=user.pk, purchase_date=timezone.now(), total_amount=Decimal(
        '5.00'), total_installments_count=1, status=Purchase.Status.OPEN, created_by=user)
    PurchaseDetail.objects.create(purchase=purchase, product=p, quantity=2, unit_price_at_purchase=p.unit_price, subtotal=(
        p.unit_price * 2).quantize(Decimal('0.01')))

    out = purchase_services.get_user_purchases(user_id=user.pk)
    assert out['success'] is True
    assert out['data']['count'] == 1
    assert out['data']['purchases'][0]['id'] == purchase.pk


@pytest.mark.django_db
def test_update_purchase_status_permissions(user):
    other = User.objects.create(username='other')
    purchase = Purchase.objects.create(user_id=user.pk, purchase_date=timezone.now(), total_amount=Decimal(
        '1.00'), total_installments_count=1, status=Purchase.Status.OPEN, created_by=user)

    # other (non-admin) cannot update purchase they don't own
    with pytest.raises(PermissionError):
        purchase_services.update_purchase_status(
            purchase_id=purchase.pk, new_status=Purchase.Status.PAID, user_id=other.pk)


@pytest.mark.django_db
def test_update_purchase_installments_and_discount(user):
    purchase = Purchase.objects.create(user_id=user.pk, purchase_date=timezone.now(), total_amount=Decimal(
        '100.00'), total_installments_count=2, status=Purchase.Status.OPEN, created_by=user)

    resp = purchase_services.update_purchase_installments(
        purchase_id=purchase.pk, new_installments_count=3, user_id=user.pk)
    assert resp['success'] is True
    purchase.refresh_from_db()
    assert purchase.total_installments_count == 3

    # update discount happy path
    # create detail so subtotal >= discount
    p = Product.objects.create(
        product_code='D1', name='D1', unit_price=Decimal('10.00'))
    PurchaseDetail.objects.create(purchase=purchase, product=p, quantity=2, unit_price_at_purchase=p.unit_price, subtotal=(
        p.unit_price * 2).quantize(Decimal('0.01')))

    disc_resp = purchase_services.update_purchase_discount(
        purchase_id=purchase.pk, new_discount=Decimal('5.00'), user_id=user.pk)
    assert disc_resp['success'] is True
