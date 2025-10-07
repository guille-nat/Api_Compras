import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from django.db.models.deletion import ProtectedError

from api.purchases.models import Purchase, PurchaseDetail
from api.products.models import Product

User = get_user_model()


@pytest.mark.django_db
def test_purchase_defaults_and_fields():
    """Verifica creación mínima de Purchase y valores por defecto."""
    user = User.objects.create(
        username="buyer", email="buyer@example.com", password="pwd")
    p = Purchase.objects.create(user=user, purchase_date=timezone.now())

    assert p.pk is not None
    assert p.total_amount == Decimal('0')
    assert p.total_installments_count == 1
    assert p.status == Purchase.Status.OPEN
    assert p.discount_applied == Decimal('0')
    assert p.created_at is not None


@pytest.mark.django_db
def test_purchase_detail_creation_and_subtotal_and_relation():
    """Verifica PurchaseDetail guarda subtotal y relación purchase.details funciona."""
    user = User.objects.create(
        username="buyer2", email="b2@example.com", password="pwd")
    prod = Product.objects.create(
        product_code="PRX1", name="Prod X", unit_price=Decimal('15.00'))
    p = Purchase.objects.create(user=user, purchase_date=timezone.now())

    qty = 3
    unit_price = Decimal('15.00')
    subtotal = unit_price * qty

    detail = PurchaseDetail.objects.create(
        purchase=p,
        product=prod,
        quantity=qty,
        unit_price_at_purchase=unit_price,
        subtotal=subtotal
    )

    # relación reverse (consulta explícita para evitar advertencias del analizador)
    details_qs = PurchaseDetail.objects.filter(purchase=p)
    assert details_qs.count() == 1
    d = details_qs.first()
    assert d is not None
    assert d.pk == detail.pk
    assert d.subtotal == subtotal


@pytest.mark.django_db
def test_product_protect_from_deletion_when_in_purchase_detail():
    """Producto referenciado por PurchaseDetail usa on_delete=PROTECT y previene borrado."""
    user = User.objects.create(
        username="buyer3", email="b3@example.com", password="pwd")
    prod = Product.objects.create(
        product_code="PRX2", name="Prod Y", unit_price=Decimal('8.00'))
    p = Purchase.objects.create(user=user, purchase_date=timezone.now())

    PurchaseDetail.objects.create(purchase=p, product=prod, quantity=1,
                                  unit_price_at_purchase=Decimal('8.00'), subtotal=Decimal('8.00'))

    with pytest.raises(ProtectedError):
        prod.delete()


@pytest.mark.django_db
def test_purchase_delete_cascades_details():
    """Al borrar una Purchase, sus PurchaseDetail asociados deben eliminarse (CASCADE)."""
    user = User.objects.create(
        username="buyer4", email="b4@example.com", password="pwd")
    prod = Product.objects.create(
        product_code="PRX3", name="Prod Z", unit_price=Decimal('20.00'))
    p = Purchase.objects.create(user=user, purchase_date=timezone.now())

    PurchaseDetail.objects.create(purchase=p, product=prod, quantity=2,
                                  unit_price_at_purchase=Decimal('20.00'), subtotal=Decimal('40.00'))
    # use IDs for filtering after delete to avoid ValueError about unsaved instances
    assert PurchaseDetail.objects.filter(purchase_id=p.pk).count() == 1

    p.delete()
    assert PurchaseDetail.objects.filter(purchase_id=p.pk).count() == 0
