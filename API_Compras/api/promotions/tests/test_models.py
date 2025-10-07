import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from api.promotions.models import (
    Promotion, PromotionScopeCategory, PromotionScopeProduct,
    PromotionScopeLocation, PromotionRule
)
from api.categories.models import Category
from api.products.models import Product
from api.storage_location.models import StorageLocation

User = get_user_model()


@pytest.mark.django_db
def test_promotion_creation_and_defaults():
    """Como tester: verificar creación básica y valores por defecto de Promotion."""
    promo = Promotion.objects.create(name="Black Friday")
    assert promo.pk is not None
    # por defecto debe venir inactiva
    assert promo.active is False
    # campos de auditoría nulos por defecto
    assert promo.created_by is None
    assert promo.updated_by is None
    assert promo.created_at is not None
    assert promo.updated_at is not None


@pytest.mark.django_db
def test_promotion_scopes_linking():
    """Verificar que las tablas scope pueden vincular promotion con category/product/location."""
    promo = Promotion.objects.create(name="Promo X", active=True)
    cat = Category.objects.create(name="Electrónica")
    prod = Product.objects.create(
        product_code="PX1", name="Prod X", unit_price=Decimal('100.00'))
    loc = StorageLocation.objects.create(
        name="Dep1", street="Calle", street_number="10", state="S", city="C", country="Ct"
    )

    psc = PromotionScopeCategory.objects.create(promotion=promo, category=cat)
    psp = PromotionScopeProduct.objects.create(promotion=promo, product=prod)
    psl = PromotionScopeLocation.objects.create(promotion=promo, location=loc)

    assert psc.pk is not None and psp.pk is not None and psl.pk is not None

    # se pueden recuperar por promotion
    cats = PromotionScopeCategory.objects.filter(promotion=promo)
    prods = PromotionScopeProduct.objects.filter(promotion=promo)
    locs = PromotionScopeLocation.objects.filter(promotion=promo)

    assert cats.count() == 1
    assert prods.count() == 1
    assert locs.count() == 1

    # campos de auditoría son nulos por defecto
    assert psc.created_by is None
    assert psp.updated_by is None


@pytest.mark.django_db
def test_promotion_rule_creation_and_fields():
    """Verificar creación de PromotionRule y lógica mínima de sus campos."""
    promo = Promotion.objects.create(name="Promo Rules")
    start = timezone.now()
    end = start + timedelta(days=7)

    # crear regla tipo percentage
    rule = PromotionRule.objects.create(
        promotion=promo,
        type=PromotionRule.Type.PERCENTAGE,
        value=Decimal('10.00'),
        priority=200,
        start_at=start,
        end_at=end,
        acumulable=True
    )

    assert rule.pk is not None
    assert rule.type == PromotionRule.Type.PERCENTAGE
    assert rule.value == Decimal('10.00')
    assert rule.priority == 200
    assert rule.acumulable is True
    # comparar timestamps para evitar advertencias del analizador estático
    assert rule.start_at.timestamp() < rule.end_at.timestamp()
    assert rule.created_by is None

    # crear otra regla con distinto priority y verificar que se guarda
    rule2 = PromotionRule.objects.create(
        promotion=promo,
        type=PromotionRule.Type.AMOUNT,
        value=Decimal('5.00'),
        priority=50,
        start_at=start,
        end_at=end
    )
    assert rule2.priority == 50


@pytest.mark.django_db
def test_promotion_rule_time_boundary_and_invalid_logic():
    """Como tester: aseguro que el sistema pueda almacenar reglas cuyo rango sea válido, y pruebo el caso start> end (sin validación automática)."""
    promo = Promotion.objects.create(name="Promo Time")
    now = timezone.now()

    # caso válido
    r = PromotionRule.objects.create(
        promotion=promo,
        type=PromotionRule.Type.FIRST_PURCHASE,
        value=Decimal('0.00'),
        priority=10,
        start_at=now,
        end_at=now + timedelta(days=1)
    )
    assert r.start_at.timestamp() < r.end_at.timestamp()

    # caso inválido: start_after_end -> el modelo no valida por defecto, debe almacenarlo
    r2 = PromotionRule.objects.create(
        promotion=promo,
        type=PromotionRule.Type.PERCENTAGE,
        value=Decimal('15.00'),
        priority=5,
        start_at=now + timedelta(days=2),
        end_at=now + timedelta(days=1)
    )
    # Como tester verifico que el sistema guarda el registro (no hay clean() automático)
    assert r2.start_at.timestamp() > r2.end_at.timestamp()
