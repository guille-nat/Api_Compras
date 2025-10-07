import pytest
from django.db import IntegrityError
from datetime import date

from api.inventories.models import InventoryRecord, InventoryMovement, StockSnapshot
from api.products.models import Product
from api.storage_location.models import StorageLocation


@pytest.mark.django_db
def test_inventoryrecord_creation_and_defaults():
    """Crea un InventoryRecord mínimo y verifica defaults de batch_code y expiry_date."""
    product = Product.objects.create(product_code="P100", name="Prod 100")
    loc = StorageLocation.objects.create(
        name="Main", street="Calle", street_number="123",
        state="State", city="City", country="Country"
    )

    ir = InventoryRecord.objects.create(
        product=product, location=loc, quantity=5)
    assert ir.pk is not None
    # default batch_code y expiry_date deben aplicarse
    assert ir.batch_code == "__NULL__"
    assert ir.expiry_date == date(9999, 12, 31)


@pytest.mark.django_db
def test_inventoryrecord_unique_constraint():
    """Verifica que la constraint única (product, location, batch_code, expiry_date) se aplica."""
    product = Product.objects.create(product_code="P101", name="Prod 101")
    loc = StorageLocation.objects.create(
        name="LocA", street="Calle", street_number="1",
        state="S", city="C", country="Ct"
    )

    InventoryRecord.objects.create(product=product, location=loc, quantity=3)
    with pytest.raises(IntegrityError):
        # crear otra con los mismos valores por defecto debe fallar
        InventoryRecord.objects.create(
            product=product, location=loc, quantity=7)


@pytest.mark.django_db
def test_inventoryrecord_ordering_by_product_then_quantity():
    """Verifica el ordering: primero por product (id) y luego -quantity."""
    p = Product.objects.create(product_code="P102", name="Prod 102")
    loc = StorageLocation.objects.create(
        name="LocB", street="Calle", street_number="2",
        state="S", city="C", country="Ct"
    )

    # dos registros del mismo product con cantidades distintas
    # especificar batch_code distinto para evitar UniqueConstraint sobre campos con valores por defecto
    InventoryRecord.objects.create(
        product=p, location=loc, quantity=5, batch_code="B1")
    InventoryRecord.objects.create(
        product=p, location=loc, quantity=12, batch_code="B2")

    records = list(InventoryRecord.objects.filter(product=p))
    quantities = [r.quantity for r in records]
    # debido a ordering = ['product', '-quantity'] las cantidades deben venir 12 luego 5
    assert quantities == sorted(quantities, reverse=True)


@pytest.mark.django_db
def test_inventorymovement_creation_and_nullable_locations():
    """Crea un InventoryMovement verificando que from_location/to_location pueden ser nulos y choices funcionan."""
    product = Product.objects.create(product_code="P200", name="Prod 200")
    # no necesitamos locations para este movimiento
    mov = InventoryMovement.objects.create(
        product=product,
        quantity=2,
        reason=InventoryMovement.Reason.PURCHASE_ENTRY,
        description="Ingreso por compra",
        reference_type=InventoryMovement.RefType.PURCHASE
    )
    assert mov.pk is not None
    assert mov.from_location is None
    assert mov.to_location is None
    assert mov.reason == InventoryMovement.Reason.PURCHASE_ENTRY
    assert mov.reference_type == InventoryMovement.RefType.PURCHASE


@pytest.mark.django_db
def test_stocksnapshot_unique_constraint_and_last_movement_nullable():
    """Verifica unique constraint de StockSnapshot y que last_movement_at puede ser nulo."""
    product = Product.objects.create(product_code="P300", name="Prod 300")
    loc = StorageLocation.objects.create(
        name="LocC", street="Calle", street_number="3",
        state="S", city="C", country="Ct"
    )

    # Cuando batch_code/expiry_date son NULL, SQLite permite múltiples NULLs
    # para que la constraint se pruebe de forma fiable en sqlite usamos valores explícitos
    ss1 = StockSnapshot.objects.create(
        product=product, location=loc, quantity=10, batch_code="BB", expiry_date=date(2025, 1, 1)
    )
    assert ss1.last_movement_at is None
    with pytest.raises(IntegrityError):
        # crear otra snapshot con los mismos valores explícitos debe fallar
        StockSnapshot.objects.create(
            product=product, location=loc, quantity=5, batch_code="BB", expiry_date=date(2025, 1, 1))
