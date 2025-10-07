import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from decimal import Decimal

from api.products.models import Product, ProductCategory
from api.categories.models import Category

User = get_user_model()


@pytest.mark.django_db
def test_product_creation_and_unique_product_code():
    """Crea un producto y verifica que product_code es único."""
    p1 = Product.objects.create(
        product_code="PRD001", name="Producto 1", unit_price=Decimal('10.00'))
    assert p1.pk is not None

    with transaction.atomic():
        with pytest.raises(IntegrityError):
            Product.objects.create(
                product_code="PRD001", name="Producto duplicado", unit_price=Decimal('5.00'))


@pytest.mark.django_db
def test_productcategory_unique_and_primary_behaviour():
    """Verifica UniqueConstraint de ProductCategory y el comportamiento de set_primary_category/get_primary_category."""
    user = User.objects.create(
        username="prod_user", email="pu@example.com", password="pwd")
    prod = Product.objects.create(
        product_code="PRD002", name="Producto 2", unit_price=Decimal('20.00'))
    cat1 = Category.objects.create(name="Cat A")
    cat2 = Category.objects.create(name="Cat B")

    # crear relaciones product-category
    pc1 = ProductCategory.objects.create(
        product=prod, category=cat1, is_primary=False)
    pc2 = ProductCategory.objects.create(
        product=prod, category=cat2, is_primary=False)
    assert pc1.pk is not None and pc2.pk is not None

    # unique constraint: intentar crear otra relación igual debe fallar
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            ProductCategory.objects.create(product=prod, category=cat1)

    # inicialmente no hay categoría primaria
    assert prod.get_primary_category() is None

    # establecer cat1 como primaria
    prod.set_primary_category(cat1, user=user)
    prod.refresh_from_db()
    # recargar product-category
    pc1.refresh_from_db()
    pc2.refresh_from_db()

    assert pc1.is_primary is True
    assert pc1.assigned_by == user
    primary = prod.get_primary_category()
    assert primary is not None
    assert primary.pk == cat1.pk

    # cambiar la primaria a cat2
    prod.set_primary_category(cat2)
    pc1.refresh_from_db()
    pc2.refresh_from_db()
    assert pc1.is_primary is False
    assert pc2.is_primary is True
    primary = prod.get_primary_category()
    assert primary is not None
    assert primary.pk == cat2.pk

    # si intentamos establecer una categoría que no está asociada debe lanzar ValueError
    cat3 = Category.objects.create(name="Cat C")
    with pytest.raises(ValueError):
        prod.set_primary_category(cat3)
