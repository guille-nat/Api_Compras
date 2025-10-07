"""Tests for purchases.serializers.PurchaseSerializer

These tests focus on create() logic: product existence, stock checks,
installments computation and discount application.
"""
from decimal import Decimal
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_purchase_serializer_create_happy_path(monkeypatch):
    """Creating a purchase should create Purchase, PurchaseDetail and Installments

    Requirements asserted:
    - total_amount computed correctly
    - product stock is decremented
    - installments are created according to total_installments_count
    """
    from api.products.models import Product
    from api.purchases.serializers import PurchaseSerializer
    from api.payments.models import Installment

    # Create a product with stock (attach stock as dynamic attribute so tests
    # remain independent of whether Product has a DB 'stock' field)
    p = Product.objects.create(
        product_code="P100", name="Prod 100", unit_price=Decimal("10.00"))
    p.stock = 10

    # Monkeypatch Product.objects.filter(...).select_for_update() to return our instance
    class FakeQS:
        def __init__(self, items):
            self._items = items

        def select_for_update(self):
            return self._items

    monkeypatch.setattr(Product.objects, "filter",
                        lambda **kwargs: FakeQS([p]))

    # Track bulk_update calls (serializer calls bulk_update to persist stock)
    called = {"n": 0}

    def fake_bulk_update(objs, fields):
        called["n"] += 1
    monkeypatch.setattr(Product.objects, "bulk_update", fake_bulk_update)

    payload = {
        "purchase_date": timezone.now(),
        "total_installments_count": 2,
        "discount_applied": "0",
        "details": [
            {"product": p.id, "cant_product": 3}
        ]
    }

    serializer = PurchaseSerializer(data=payload)
    assert serializer.is_valid(), f"serializer errors: {serializer.errors}"
    User = get_user_model()
    user = User.objects.create_user(
        username="u_test1", email="u1@example.com", password="pwd")
    purchase = serializer.save(user=user)

    # total_amount should be 3 * 10.00 = 30.00 (no discount, no surcharge for 2 installments)
    assert Decimal(purchase.total_amount).quantize(
        Decimal("0.01")) == Decimal("30.00")

    # bulk_update should have been called to persist stock
    assert called["n"] == 1

    # installments created
    insts = Installment.objects.filter(purchase=purchase)
    assert insts.count() == 2


@pytest.mark.django_db
def test_purchase_serializer_create_insufficient_stock(monkeypatch):
    from api.products.models import Product
    from api.purchases.serializers import PurchaseSerializer

    p = Product.objects.create(
        product_code="P101", name="Prod 101", unit_price=Decimal("5.00"))
    p.stock = 1

    class FakeQS:
        def __init__(self, items):
            self._items = items

        def select_for_update(self):
            return self._items

    monkeypatch.setattr(Product.objects, "filter",
                        lambda **kwargs: FakeQS([p]))

    payload = {
        "purchase_date": timezone.now(),
        "total_installments_count": 1,
        "discount_applied": "0",
        "details": [
            {"product": p.id, "cant_product": 2}
        ]
    }

    serializer = PurchaseSerializer(data=payload)
    # create a user for serializer.save if it gets that far
    User = get_user_model()
    _ = User.objects.create_user(
        username="u_test2", email="u2@example.com", password="pwd")
    assert not serializer.is_valid(), "serializer should be invalid due to insufficient stock"
    assert any("insuficiente" in str(e) or "insufficient" in str(e)
               for e in serializer.errors), serializer.errors


@pytest.mark.django_db
def test_purchase_serializer_create_with_discount_and_surcharge(monkeypatch):
    from api.products.models import Product
    from api.purchases.serializers import PurchaseSerializer

    p = Product.objects.create(
        product_code="P102", name="Prod 102", unit_price=Decimal("20.00"))
    p.stock = 100

    class FakeQS:
        def __init__(self, items):
            self._items = items

        def select_for_update(self):
            return self._items

    monkeypatch.setattr(Product.objects, "filter",
                        lambda **kwargs: FakeQS([p]))

    called = {"n": 0}
    monkeypatch.setattr(Product.objects, "bulk_update", lambda objs,
                        fields: called.__setitem__("n", called.get("n", 0) + 1))

    # Use 12 installments -> surcharge 45%
    payload = {
        "purchase_date": timezone.now(),
        "total_installments_count": 12,
        "discount_applied": "10",  # 10% discount
        "details": [
            {"product": p.id, "cant_product": 1}
        ]
    }

    serializer = PurchaseSerializer(data=payload)
    assert serializer.is_valid(), serializer.errors
    User = get_user_model()
    user = User.objects.create_user(
        username="u_test3", email="u3@example.com", password="pwd")
    purchase = serializer.save(user=user)

    # base = 20.00, surcharge 45% => 29.00, discount 10% => 26.10
    assert Decimal(purchase.total_amount).quantize(
        Decimal("0.01")) == Decimal("26.10")
