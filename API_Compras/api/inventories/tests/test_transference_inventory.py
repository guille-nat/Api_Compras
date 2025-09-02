import pytest
from django.utils import timezone
from django.core import exceptions
from api.products.models import Product
from api.storage_location.models import StorageLocation
from api.inventories.models import InventoryRecord, InventoryMovement
from api.inventories.services import transference_inventory
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="tester", password="x")


@pytest.fixture
def product(db):
    return Product.objects.create(
        product_code="P-001", name="Prod 1", brand="B", model="M", unit_price=100
    )


@pytest.fixture
def loc_from(db):
    return StorageLocation.objects.create(
        name="Depo A", address="x", state="SF", city="Rosario", country="AR", type="WAREHOUSE"
    )


@pytest.fixture
def loc_to(db):
    return StorageLocation.objects.create(
        name="Depo B", address="y", state="SF", city="Rosario", country="AR", type="WAREHOUSE"
    )


@pytest.mark.django_db
def test_transfer_single_record_exact_amount_deletes_origin_and_creates_movement(user, product, loc_from, loc_to):
    ir_from = InventoryRecord.objects.create(
        product=product, location=loc_from, quantity=10)

    result = transference_inventory(
        product=product,
        from_location=loc_from,
        to_location=loc_to,
        description="Move simple",
        quantity=10,
        reference_id=123,
        user=user,
    )

    assert result["moved"] == 10
    assert result["movements_count"] == 1

    # origen eliminado
    assert not InventoryRecord.objects.filter(pk=ir_from.pk).exists()

    # destino consolidado (batch/expiry None)
    ir_to = InventoryRecord.objects.get(
        product=product, location=loc_to, batch_code=None, expiry_date=None)
    assert ir_to.quantity == 10

    mv = InventoryMovement.objects.get()
    assert mv.product == product
    assert mv.from_location == loc_from
    assert mv.to_location == loc_to
    assert mv.quantity == 10
    assert mv.reason == InventoryMovement.Reason.TRANSFER
    assert mv.reference_type == InventoryMovement.RefType.MANUAL
    assert mv.reference_id == 123
    assert mv.created_by == user
    assert mv.updated_by == user


@pytest.mark.django_db
def test_transfer_partial_amount_leaves_origin_with_remainder(user, product, loc_from, loc_to):
    ir_from = InventoryRecord.objects.create(
        product=product, location=loc_from, quantity=10)

    transference_inventory(
        product=product,
        from_location=loc_from,
        to_location=loc_to,
        description="Move partial",
        quantity=4,
        reference_id=1,
        user=user,
    )

    ir_from.refresh_from_db()
    assert ir_from.quantity == 6

    ir_to = InventoryRecord.objects.get(
        product=product, location=loc_to, batch_code=None, expiry_date=None)
    assert ir_to.quantity == 4

    mv = InventoryMovement.objects.get()
    assert mv.quantity == 4


@pytest.mark.django_db
def test_transfer_fefo_two_batches_consumes_earliest_first(user, product, loc_from, loc_to):
    # dos lotes con distintos vencimientos
    exp1 = timezone.datetime(2025, 9, 1).date()
    exp2 = timezone.datetime(2025, 12, 1).date()
    ir1 = InventoryRecord.objects.create(
        product=product, location=loc_from, quantity=5, batch_code="L1", expiry_date=exp1)
    ir2 = InventoryRecord.objects.create(
        product=product, location=loc_from, quantity=10, batch_code="L2", expiry_date=exp2)

    result = transference_inventory(
        product=product,
        from_location=loc_from,
        to_location=loc_to,
        description="FEFO",
        quantity=7,
        reference_id=77,
        user=user,
    )

    assert result["moved"] == 7
    assert result["movements_count"] == 2

    # ir1 debe borrarse (0), ir2 queda con 8
    assert not InventoryRecord.objects.filter(pk=ir1.pk).exists()
    ir2.refresh_from_db()
    assert ir2.quantity == 8

    # destino: dos IR distintos por lote/fecha
    dest_l1 = InventoryRecord.objects.get(
        product=product, location=loc_to, batch_code="L1", expiry_date=exp1)
    dest_l2 = InventoryRecord.objects.get(
        product=product, location=loc_to, batch_code="L2", expiry_date=exp2)
    assert dest_l1.quantity == 5
    assert dest_l2.quantity == 2

    # dos movimientos (uno por tramo)
    assert InventoryMovement.objects.count() == 2
    assert set(InventoryMovement.objects.values_list(
        "quantity", flat=True)) == {5, 2}


@pytest.mark.django_db
def test_transfer_consolidates_into_existing_destination_record(user, product, loc_from, loc_to):
    ir_from = InventoryRecord.objects.create(
        product=product, location=loc_from, quantity=3, batch_code="L1")
    ir_to = InventoryRecord.objects.create(
        product=product, location=loc_to, quantity=7, batch_code="L1")

    transference_inventory(
        product=product,
        from_location=loc_from,
        to_location=loc_to,
        description="Consolidate",
        quantity=2,
        reference_id=5,
        user=user,
    )

    ir_to.refresh_from_db()
    assert ir_to.quantity == 9

    ir_from.refresh_from_db()
    assert ir_from.quantity == 1


@pytest.mark.django_db
def test_error_when_no_stock(user, product, loc_from, loc_to):
    with pytest.raises(exceptions.ValidationError) as ei:
        transference_inventory(
            product=product,
            from_location=loc_from,
            to_location=loc_to,
            description="Fail",
            quantity=1,
            reference_id=1,
            user=user,
        )
    assert "No hay stock en el origen" in str(ei.value)


@pytest.mark.django_db
def test_error_when_insufficient_total_stock(user, product, loc_from, loc_to):
    InventoryRecord.objects.create(
        product=product, location=loc_from, quantity=2)
    with pytest.raises(exceptions.ValidationError) as ei:
        transference_inventory(
            product=product,
            from_location=loc_from,
            to_location=loc_to,
            description="Fail",
            quantity=5,
            reference_id=1,
            user=user,
        )
    assert "Stock insuficiente en el origen" in str(ei.value)


@pytest.mark.django_db
@pytest.mark.parametrize("qty", [0, -1])
def test_error_when_quantity_invalid(user, product, loc_from, loc_to, qty):
    InventoryRecord.objects.create(
        product=product, location=loc_from, quantity=5)
    with pytest.raises(exceptions.ValidationError):
        transference_inventory(
            product=product,
            from_location=loc_from,
            to_location=loc_to,
            description="Invalid qty",
            quantity=qty,
            reference_id=1,
            user=user,
        )


@pytest.mark.django_db
def test_error_when_same_origin_and_destination(user, product, loc_from):
    InventoryRecord.objects.create(
        product=product, location=loc_from, quantity=5)
    with pytest.raises(exceptions.ValidationError):
        transference_inventory(
            product=product,
            from_location=loc_from,
            to_location=loc_from,           # misma
            description="Same loc",
            quantity=1,
            reference_id=1,
            user=user,
        )
