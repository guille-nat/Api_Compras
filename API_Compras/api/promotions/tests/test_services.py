import pytest
from datetime import timedelta, date
from decimal import Decimal
from django.utils import timezone

from django.contrib.auth import get_user_model

from api.promotions import services as promotion_services
from api.promotions.models import Promotion, PromotionRule, PromotionScopeCategory, PromotionScopeProduct, PromotionScopeLocation
from api.categories.models import Category
from api.products.models import Product
from api.storage_location.models import StorageLocation


User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create(username='promo_user', email='promo@example.com')


@pytest.mark.django_db
def test_create_promotion_happy(user):
    promo = promotion_services.create_promotion(
        name='  SUMMER Sale  ', active=True, user_id=user.pk)
    assert isinstance(promo, Promotion)
    assert promo.name == 'summer sale'  # normalized
    assert promo.active is True
    assert promo.created_by == user


@pytest.mark.django_db
def test_create_promotion_duplicate(user):
    promotion_services.create_promotion(
        name='XMAS', active=False, user_id=user.pk)
    with pytest.raises(ValueError):
        promotion_services.create_promotion(
            name='xmas', active=True, user_id=user.pk)


@pytest.mark.django_db
def test_create_rule_happy_and_date_conversion(user):
    promo = Promotion.objects.create(name='R-BASE')
    start = date.today()
    end = start + timedelta(days=2)
    rule = promotion_services.create_rule(
        promotion_id=promo.pk,
        type=PromotionRule.Type.PERCENTAGE,
        value=Decimal('10.00'),
        priority=10,
        start_date=start,
        end_date=end,
        acumulable=True,
        user_id=user.pk
    )
    assert isinstance(rule, PromotionRule)
    # service stores start_at/end_at as datetimes spanning full day
    assert rule.start_at.date() == start
    assert rule.end_at.date() == end
    assert rule.acumulable is True
    assert rule.created_by == user


@pytest.mark.django_db
def test_create_rule_invalid_dates(user):
    promo = Promotion.objects.create(name='R-INV')
    start = date.today()
    end = start
    with pytest.raises(ValueError):
        promotion_services.create_rule(
            promotion_id=promo.pk,
            type=PromotionRule.Type.PERCENTAGE,
            value=Decimal('5.00'),
            priority=1,
            start_date=start,
            end_date=end,
            acumulable=False,
            user_id=user.pk
        )


@pytest.mark.django_db
def test_create_promotion_scopes_and_duplicates(user):
    promo = Promotion.objects.create(name='ScopeTest')
    cat = Category.objects.create(name='Cat1')
    prod = Product.objects.create(
        product_code='PC1', name='Prod', unit_price=Decimal('1.00'))
    loc = StorageLocation.objects.create(
        name='Loc1', street='St', street_number='1', state='S', city='C', country='Ct')

    # first creations should succeed
    psc = promotion_services.create_promotion_category(
        promotion_id=promo.pk, category_id=cat.pk, user_id=user.pk)
    assert isinstance(psc, PromotionScopeCategory)
    psp = promotion_services.create_promotion_product(
        promotion_id=promo.pk, product_id=prod.pk, user_id=user.pk)
    assert isinstance(psp, PromotionScopeProduct)
    psl = promotion_services.create_promotion_location(
        promotion_id=promo.pk, location_id=loc.pk, user_id=user.pk)
    assert isinstance(psl, PromotionScopeLocation)

    # duplicates raise
    with pytest.raises(ValueError):
        promotion_services.create_promotion_category(
            promotion_id=promo.pk, category_id=cat.pk, user_id=user.pk)
    with pytest.raises(ValueError):
        promotion_services.create_promotion_product(
            promotion_id=promo.pk, product_id=prod.pk, user_id=user.pk)
    with pytest.raises(ValueError):
        promotion_services.create_promotion_location(
            promotion_id=promo.pk, location_id=loc.pk, user_id=user.pk)


@pytest.mark.django_db
def test_create_promotion_and_rule_full_flow(user):
    cat = Category.objects.create(name='ScopeCat')
    data = {
        'name': 'Bundle Promo',
        'type': PromotionRule.Type.AMOUNT,
        'value': '5.00',
        'start_date': (date.today()).strftime('%Y-%m-%d'),
        'end_date': (date.today() + timedelta(days=5)).strftime('%Y-%m-%d'),
        'categories_ids': [cat.pk]
    }

    res = promotion_services.create_promotion_and_rule(data, user_id=user.pk)
    assert 'promotion' in res and 'rule' in res
    assert res['promotion']['name'] == 'bundle promo'
    assert isinstance(res['rule']['value'], Decimal)
    assert res['categories'] != {}


@pytest.mark.django_db
def test_auto_deactivate_expired_promotions():
    # create an active promotion with a rule already expired
    promo = Promotion.objects.create(name='ToExpire', active=True)
    now = timezone.now()
    PromotionRule.objects.create(
        promotion=promo,
        type=PromotionRule.Type.AMOUNT,
        value=Decimal('1.00'),
        priority=1,
        start_at=now - timedelta(days=10),
        end_at=now - timedelta(days=1)
    )
    count = promotion_services.auto_deactivate_expired_promotions()
    assert count >= 1
    promo.refresh_from_db()
    assert promo.active is False


@pytest.mark.django_db
def test_update_and_delete_promotion_and_rule(user):
    promo = Promotion.objects.create(name='UpdDel', active=True)
    # update name
    resp = promotion_services.update_promotion(
        promotion_id=promo.pk, user_id=user.pk, name='UpdatedName')
    assert resp['success'] is True
    promo.refresh_from_db()
    assert promo.name == 'updatedname'

    # create a rule and update it
    rule = PromotionRule.objects.create(
        promotion=promo,
        type=PromotionRule.Type.PERCENTAGE,
        value=Decimal('2.00'),
        priority=5,
        start_at=timezone.now(),
        end_at=timezone.now() + timedelta(days=2)
    )
    rresp = promotion_services.update_rule(
        rule_id=rule.pk, user_id=user.pk, priority=10)
    assert rresp['success'] is True
    rule.refresh_from_db()
    assert rule.priority == 10

    # delete rule
    dresp = promotion_services.delete_rule(rule_id=rule.pk, user_id=user.pk)
    assert dresp['success'] is True

    # delete promotion
    prem = promotion_services.delete_promotion(
        promotion_id=promo.pk, user_id=user.pk)
    assert prem['success'] is True
    assert Promotion.objects.filter(pk=promo.pk).count() == 0


@pytest.mark.django_db
def test_get_active_promotions_and_discount_calculation(user):
    # create product and categories and location
    p = Product.objects.create(
        product_code='DIS-1', name='DiscProd', unit_price=Decimal('100.00'))
    cat = Category.objects.create(name='DiscCat')
    # not used directly, ensure relation exists
    ProductCategory = getattr(p, 'categories')
    Product.objects.filter(pk=p.pk).update()

    # promotion with category scope and percentage acumulable
    promo = Promotion.objects.create(name='DiscPromo', active=True)
    start = timezone.now() - timedelta(days=1)
    end = timezone.now() + timedelta(days=5)
    pr = PromotionRule.objects.create(
        promotion=promo,
        type=PromotionRule.Type.PERCENTAGE,
        value=Decimal('10.00'),
        priority=100,
        start_at=start,
        end_at=end,
        acumulable=True
    )
    PromotionScopeCategory.objects.create(promotion=promo, category=cat)
    # link product to category
    from api.products.models import ProductCategory
    ProductCategory.objects.create(
        product=p, category=cat, is_primary=True, assigned_by=user)

    promos_for_cat = promotion_services.get_active_promotions_category(
        category_id=cat.pk)
    assert isinstance(promos_for_cat, list)
    assert any(pr_data['id'] == promo.pk for pr_data in promos_for_cat)

    # calculate discounted price
    discounted = promotion_services.calculate_discounted_price_product(p)
    assert discounted < p.unit_price
