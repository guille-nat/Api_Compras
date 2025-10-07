import pytest
from django.core import exceptions
from django.utils import timezone
from datetime import timedelta

from api.categories.services import create_category, rename_category, get_all_categories_with_promotions
from api.categories.models import Category
from api.promotions.models import Promotion, PromotionRule, PromotionScopeCategory
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()


@pytest.mark.django_db
def test_create_category_success_and_normalization():
    """Crea categoría con usuario y verifica normalización y retorno esperado."""
    user = User.objects.create(
        username="creator", email="c@example.com", password="pwd")
    result = create_category(user=user, name="  NewCategory ")
    assert result["success"] is True
    cat = result["data"]
    assert isinstance(cat, Category)
    # name normalizado y en minúsculas sin espacios
    assert cat.name == "newcategory"
    assert cat.created_by == user


@pytest.mark.django_db
def test_create_category_duplicate_raises_validation_error():
    """Si ya existe (case-insensitive) debe lanzar ValidationError."""
    user = User.objects.create(
        username="c2", email="c2@example.com", password="pwd")
    Category.objects.create(name="ropa")
    with pytest.raises(exceptions.ValidationError):
        create_category(user=user, name=" ROPA ")


@pytest.mark.django_db
def test_rename_category_success_and_updated_by():
    """Renombrado válido: chequear datos retornados y updated_by."""
    user = User.objects.create(
        username="editor", email="ed@example.com", password="pwd")
    cat = Category.objects.create(name="alimentos")

    res = rename_category(user=user, category=cat, new_name=" Comestibles ")
    assert res["success"] is True
    data = res["data"]
    assert data["old_name"] == "alimentos"
    assert data["new_name"] == "comestibles"
    # el objeto category devuelto debe reflejar el nuevo nombre
    cat.refresh_from_db()
    assert cat.name == "comestibles"
    assert cat.updated_by == user


@pytest.mark.django_db
def test_rename_category_to_existing_name_raises():
    """Si intento renombrar a un nombre que ya existe en otra categoría -> ValidationError."""
    user = User.objects.create(
        username="editor2", email="ed2@example.com", password="pwd")
    cat1 = Category.objects.create(name="salud")
    cat2 = Category.objects.create(name="belleza")

    with pytest.raises(exceptions.ValidationError):
        rename_category(user=user, category=cat2, new_name=" Salud ")


@pytest.mark.django_db
def test_get_all_categories_with_promotions_various_cases():
    """Probar multiple combinaciones: sin promos, promo inactiva, promo activa con reglas vigentes y reglas vencidas."""
    now = timezone.now()
    # Categorías
    cat_no = Category.objects.create(name="sinpromo")
    cat_mixed = Category.objects.create(name="mixta")

    # Promoción inactiva (no debe aparecer)
    promo_inactive = Promotion.objects.create(name="Promo Off", active=False)
    PromotionScopeCategory.objects.create(
        promotion=promo_inactive, category=cat_no)

    # Promoción activa con regla vigente
    promo_active = Promotion.objects.create(name="Promo Active", active=True)
    # regla vigente
    rule_vig = PromotionRule.objects.create(
        promotion=promo_active,
        type=PromotionRule.Type.PERCENTAGE,
        value=Decimal('10.00'),
        priority=10,
        start_at=now - timedelta(days=1),
        end_at=now + timedelta(days=1),
        acumulable=True
    )
    PromotionScopeCategory.objects.create(
        promotion=promo_active, category=cat_mixed)

    # Promoción activa sin reglas vigentes (regla fuera de rango)
    promo_active_no_rules = Promotion.objects.create(
        name="Promo NoRules", active=True)
    PromotionScopeCategory.objects.create(
        promotion=promo_active_no_rules, category=cat_mixed)
    PromotionRule.objects.create(
        promotion=promo_active_no_rules,
        type=PromotionRule.Type.AMOUNT,
        value=Decimal('5.00'),
        priority=5,
        start_at=now - timedelta(days=10),
        end_at=now - timedelta(days=5),
        acumulable=False
    )

    # Ejecutar el servicio
    res = get_all_categories_with_promotions()
    assert res["success"] is True
    data = res["data"]

    # Encontrar entradas por categoría
    by_name = {entry['category']['name']: entry for entry in data}

    # cat_no tiene promotion inactiva -> active_promotions empty
    assert "sinpromo" in by_name
    assert by_name["sinpromo"]["active_promotions"] == []

    # cat_mixed debe tener dos promociones (promo_active y promo_active_no_rules)
    assert "mixta" in by_name
    active_promos = by_name["mixta"]["active_promotions"]
    names = {p['name'] for p in active_promos}
    assert "Promo Active" in names
    assert "Promo NoRules" in names

    # la promo con regla vigente debe exponer una regla en 'rules'
    pa = next(p for p in active_promos if p['name'] == "Promo Active")
    assert len(pa['rules']) == 1
    r = pa['rules'][0]
    assert set(r.keys()) >= {"id", "type", "value",
                             "priority", "start_at", "end_at", "acumulable"}

    # la otra promo no tiene reglas vigentes
    pnr = next(p for p in active_promos if p['name'] == "Promo NoRules")
    assert pnr['rules'] == []


@pytest.mark.django_db
def test_get_all_categories_with_no_categories_returns_empty_list():
    """Cuando no hay categorías, debe devolver data como lista vacía."""
    # asegurar que no hay categorías
    Category.objects.all().delete()
    res = get_all_categories_with_promotions()
    assert res["success"] is True
    assert res["data"] == []
