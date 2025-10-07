import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from api.storage_location.models import StorageLocation
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_storage_location_str_and_ordering():
    """Verifica __str__ y ordering por name."""
    l1 = StorageLocation.objects.create(
        name="Bodega Z", street="Calle", street_number="10",
        state="S", city="C", country="Ct", type="WH"
    )
    l2 = StorageLocation.objects.create(
        name="Almacen A", street="Otra", street_number="20",
        state="S", city="C", country="Ct", type="SB"
    )

    # __str__ incluye el name y la etiqueta del tipo
    assert str(l1) == f"{l1.name} [{l1.get_type_display()}]"

    names = list(StorageLocation.objects.values_list("name", flat=True))
    assert names == sorted(names)


@pytest.mark.django_db
def test_unique_constraint_parent_type_name():
    """Verifica UniqueConstraint en (parent, type, name)."""
    parent = StorageLocation.objects.create(
        name="Parent", street="C1", street_number="1", state="S", city="C", country="Ct"
    )

    StorageLocation.objects.create(
        name="Shelf1", street="S1", street_number="2", state="S", city="C", country="Ct",
        parent=parent, type="SH"
    )

    with transaction.atomic():
        with pytest.raises(IntegrityError):
            # crear otra con los mismos parent, type y name debe fallar
            StorageLocation.objects.create(
                name="Shelf1", street="S1", street_number="3", state="S", city="C", country="Ct",
                parent=parent, type="SH"
            )


@pytest.mark.django_db
def test_protect_on_delete_parent():
    """El parent tiene on_delete=PROTECT: borrar padre debe lanzar ProtectedError si hay hijos."""
    parent = StorageLocation.objects.create(
        name="P", street="C", street_number="5", state="S", city="C", country="Ct"
    )
    child = StorageLocation.objects.create(
        name="Child", street="C2", street_number="6", state="S", city="C", country="Ct",
        parent=parent
    )

    with pytest.raises(ProtectedError):
        parent.delete()


@pytest.mark.django_db
def test_clean_prevents_parent_self_assignment():
    """El método clean debe evitar que un StorageLocation sea padre de sí mismo."""
    loc = StorageLocation.objects.create(
        name="Solo", street="C", street_number="7", state="S", city="C", country="Ct"
    )

    # Asignar parent a sí mismo y ejecutar full_clean() debe lanzar ValidationError
    loc.parent = loc
    with pytest.raises(ValidationError):
        loc.full_clean()

    # Asignar parent distinto no debe lanzar
    other = StorageLocation.objects.create(
        name="Otro", street="C", street_number="8", state="S", city="C", country="Ct"
    )
    loc.parent = other
    # debería limpiar sin errores
    loc.full_clean()
