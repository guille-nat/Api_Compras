import pytest
from django.core import exceptions
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from api.inventories.services import (
    transference_inventory, purchase_entry_inventory, exit_sale_inventory,
    adjustment_inventory, return_output_inventory, return_entry_inventory, get_inventory_record
)
from api.inventories.models import InventoryRecord, InventoryMovement
from api.products.models import Product
from api.storage_location.models import StorageLocation
from api.users.models import CustomUser
from api.categories.models import Category


@pytest.fixture
def user(db):
    return CustomUser.objects.create(username="tester", email="t@example.com", password="pwd")


@pytest.fixture
def product(db):
    return Product.objects.create(product_code="P-001", name="Producto 1")


@pytest.fixture
def locations(db, user):
    l1 = StorageLocation.objects.create(
        name="Almacen A", street="Calle", street_number="1", state="ST", city="C", country="CO", created_by=user
    )
    l2 = StorageLocation.objects.create(
        name="Almacen B", street="Calle", street_number="2", state="ST", city="C", country="CO", created_by=user
    )
    return l1, l2


@pytest.mark.django_db
def test_purchase_entry_creates_and_updates_records(product, locations, user):
    to_location = locations[0]
    # Crear entrada sin batch/expiry
    res = purchase_entry_inventory(product=product, to_location=to_location, expiry_date=None, batch_code=None,
                                   description="Compra", quantity=5, reference_id=1, user=user)
    assert res["success"]
    inv = InventoryRecord.objects.get(
        product=product, location=to_location, batch_code="__NULL__")
    assert inv.quantity == 5

    # Segunda entrada con el mismo batch -> debe acumular
    res2 = purchase_entry_inventory(product=product, to_location=to_location, expiry_date=None, batch_code=None,
                                    description="Compra2", quantity=3, reference_id=2, user=user)
    inv.refresh_from_db()
    assert inv.quantity == 8


@pytest.mark.django_db
def test_transference_happy_path_consumes_and_creates_movements(product, locations, user):
    from_loc, to_loc = locations
    # Pre-popular origen con dos InventoryRecord (dos lotes) para FEFO
    InventoryRecord.objects.create(product=product, location=from_loc, quantity=2,
                                   batch_code="A", expiry_date=date(2025, 12, 1), updated_by=user)
    InventoryRecord.objects.create(product=product, location=from_loc, quantity=5,
                                   batch_code="B", expiry_date=date(2026, 1, 1), updated_by=user)

    # Transferir 6 unidades => consume 2 del lote A y 4 del B
    res = transference_inventory(product=product, from_location=from_loc, to_location=to_loc,
                                 description="Transf", quantity=6, reference_id=10, user=user)
    assert res["success"]
    assert res["data"]["moved"] == 6
    # Movements created
    assert InventoryMovement.objects.filter(
        product=product, from_location=from_loc, to_location=to_loc).count() == 2
    # Origen registros actualizados/deleted
    assert InventoryRecord.objects.filter(
        product=product, location=from_loc).count() == 1


@pytest.mark.django_db
def test_transference_invalid_quantity_and_same_location_raises(product, locations, user):
    from_loc, to_loc = locations
    with pytest.raises(exceptions.ValidationError):
        transference_inventory(product=product, from_location=from_loc, to_location=from_loc,
                               description="X", quantity=1, reference_id=1, user=user)
    with pytest.raises(exceptions.ValidationError):
        transference_inventory(product=product, from_location=from_loc, to_location=to_loc,
                               description="X", quantity=0, reference_id=1, user=user)


@pytest.mark.django_db
def test_transference_insufficient_stock_raises(product, locations, user):
    from_loc, to_loc = locations
    InventoryRecord.objects.create(product=product, location=from_loc, quantity=2,
                                   batch_code="A", expiry_date=date(2025, 12, 1), updated_by=user)
    with pytest.raises(exceptions.ValidationError):
        transference_inventory(product=product, from_location=from_loc, to_location=to_loc,
                               description="T", quantity=5, reference_id=1, user=user)


@pytest.mark.django_db
def test_exit_sale_happy_and_insufficient(product, locations, user):
    from_loc, _ = locations
    InventoryRecord.objects.create(product=product, location=from_loc, quantity=4,
                                   batch_code="A", expiry_date=date(2025, 12, 1), updated_by=user)
    res = exit_sale_inventory(product=product, from_location=from_loc,
                              description="Venta", quantity=3, reference_id=100, user=user)
    assert res["success"]
    assert res["data"]["moved"] == 3

    # ahora intentar mayor a disponible
    with pytest.raises(exceptions.ValidationError):
        exit_sale_inventory(product=product, from_location=from_loc,
                            description="Venta2", quantity=5, reference_id=101, user=user)


@pytest.mark.django_db
def test_adjustment_inventory_aggregate_remove_and_adjust_other(product, locations, user):
    from_loc, other_loc = locations
    # crear registro base
    InventoryRecord.objects.create(product=product, location=from_loc, quantity=10,
                                   batch_code="X", expiry_date=date(2025, 12, 31), updated_by=user)

    # Agregar
    res = adjustment_inventory(product=product, from_location=from_loc, expiry_date=date(2025, 12, 31), batch_code="X",
                               description="Adj", quantity=5, reference_id=200, user=user, aggregate=True, remove=None, adjusted_other=None,
                               modify_expiry_date=None, modify_batch_code=None, modify_location=None)
    assert res["success"]
    inv = InventoryRecord.objects.get(
        product=product, location=from_loc, batch_code="X")
    assert inv.quantity == 15

    # Quitar con suficiente stock
    res2 = adjustment_inventory(product=product, from_location=from_loc, expiry_date=date(2025, 12, 31), batch_code="X",
                                description="Adj", quantity=5, reference_id=201, user=user, aggregate=None, remove=True, adjusted_other=None,
                                modify_expiry_date=None, modify_batch_code=None, modify_location=None)
    assert res2["success"]
    inv.refresh_from_db()
    assert inv.quantity == 10

    # Ajustar a otra ubicacion (modify_location) pero passing a non-existing -> should raise
    fake_loc = StorageLocation(pk=9999, name="fake", street="s",
                               street_number="1", state="ST", city="C", country="CO")
    with pytest.raises(exceptions.ValidationError):
        adjustment_inventory(product=product, from_location=from_loc, expiry_date=date(2025, 12, 31), batch_code="X",
                             description="Adj", quantity=1, reference_id=202, user=user, aggregate=None, remove=None, adjusted_other=True,
                             modify_expiry_date=None, modify_batch_code="NEW", modify_location=fake_loc)

    # Ajustar a otra ubicación real (create new location) -> success
    new_loc = StorageLocation.objects.create(
        name="Destino", street="S", street_number="5", state="ST", city="C", country="CO", created_by=user)
    res3 = adjustment_inventory(product=product, from_location=from_loc, expiry_date=date(2025, 12, 31), batch_code="X",
                                description="AdjMove", quantity=2, reference_id=203, user=user, aggregate=None, remove=None, adjusted_other=True,
                                modify_expiry_date=None, modify_batch_code="NEWX", modify_location=new_loc)
    assert res3["success"]
    # El inventory record original debe haberse actualizado con el nuevo batch_code y/o location según impl.


@pytest.mark.django_db
def test_return_output_and_entry_and_get_inventory_record(product, locations, user):
    from_loc, to_loc = locations
    # Primero probar return_entry_inventory (entrada por devolución) sin batch/expiry
    res = return_entry_inventory(product=product, to_location=to_loc, expiry_date=None, batch_code=None,
                                 description="Ret", quantity=7, reference_id=300, user=user)
    assert res["success"]
    inv = res["data"]["inventory"]
    assert inv.quantity == 7

    # Probar return_output_inventory saliendo de ese registro
    res2 = return_output_inventory(product=product, from_location=to_loc, expiry_date=None, batch_code=None,
                                   description="RetOut", quantity=2, reference_id=301, user=user)
    assert res2["success"]
    inv.refresh_from_db()
    assert inv.quantity == 5

    # get_inventory_record helper
    found = get_inventory_record(product_id=product.pk, location_id=to_loc.pk)
    assert found is not None

    # intento quitar más del stock -> error
    with pytest.raises(exceptions.ValidationError):
        return_output_inventory(product=product, from_location=to_loc, expiry_date=None, batch_code=None,
                                description="RetOut", quantity=20, reference_id=302, user=user)
