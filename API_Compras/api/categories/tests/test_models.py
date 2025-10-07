import pytest
from django.db import IntegrityError
from django.utils import timezone

from api.categories.models import Category


@pytest.mark.django_db
def test_category_creation_and_str():
    """Verifica que una categoría se crea correctamente y su __str__ devuelve el nombre."""
    c = Category.objects.create(name="Electronica")
    assert c.pk is not None
    assert str(c) == "Electronica"
    # timestamps created/updated must be set
    assert c.created_at is not None
    assert c.updated_at is not None


@pytest.mark.django_db
def test_unique_name_constraint():
    """Verifica que el constraint de unicidad en 'name' se cumple."""
    Category.objects.create(name="Ropa")
    with pytest.raises(IntegrityError):
        # intentar crear otra con el mismo nombre debe fallar en la BD
        Category.objects.create(name="Ropa")


@pytest.mark.django_db
def test_audit_fields_nullable_and_default():
    """Verifica que created_by y updated_by pueden ser nulos y que updated_at se actualiza."""
    c = Category.objects.create(name="Alimentos")
    assert c.created_by is None
    assert c.updated_by is None

    # force update to change updated_at
    before = c.updated_at
    c.name = "Alimentos Y Bebidas"
    c.save()
    c.refresh_from_db()
    assert c.updated_at >= before


@pytest.mark.django_db
def test_ordering_by_name():
    """Verifica que el Meta.ordering por 'name' funciona en consultas."""
    Category.objects.create(name="Zeta")
    Category.objects.create(name="Alfa")
    names = list(Category.objects.values_list("name", flat=True))
    # debe venir ordenado alfabéticamente por name
    assert names == sorted(names)
