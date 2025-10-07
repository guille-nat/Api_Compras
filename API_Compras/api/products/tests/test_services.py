import pytest
from decimal import Decimal
from django.utils import timezone
from django.core import exceptions

from api.products import services as product_services
from api.products.models import Product, ProductCategory
from api.categories.models import Category
from api.users.models import CustomUser


@pytest.fixture
def user(db):
    return CustomUser.objects.create(username="prod_user", email="prod@example.com", password="pwd")


@pytest.fixture
def categories(db, user):
    c1 = Category.objects.create(name="Cat A", created_by=user)
    c2 = Category.objects.create(name="Cat B", created_by=user)
    return c1, c2


@pytest.mark.django_db
def test_create_products_happy(user, categories):
    c1, c2 = categories
    data = {
        'products': [
            {
                'product_code': 'PR-001',
                'name': 'Product 1',
                'brand': 'BrandX',
                'model': 'M1',
                'unit_price': '12.50',
                'category_ids': [c1.pk, c2.pk],
                'primary_category_id': c1.pk
            },
            {
                'product_code': 'PR-002',
                'name': 'Product 2',
                'brand': 'BrandY',
                'model': 'M2',
                'unit_price': '20.00',
                'category_ids': [c2.pk]
            }
        ]
    }

    res = product_services.create_products(data, user_id=user.pk)
    assert res['success']
    assert res['created_count'] == 2
    # verify products exist
    assert Product.objects.filter(
        product_code__in=['PR-001', 'PR-002']).count() == 2
    # verify product-category relations
    assert ProductCategory.objects.filter(category=c1).exists()
    assert ProductCategory.objects.filter(category=c2).count() >= 2


@pytest.mark.django_db
def test_create_products_missing_key(user):
    with pytest.raises(ValueError):
        product_services.create_products({}, user_id=user.pk)


@pytest.mark.django_db
def test_create_products_duplicate_codes(user, categories):
    c1, _ = categories
    data = {
        'products': [
            {
                'product_code': 'DUP-1',
                'name': 'Dup',
                'unit_price': '5.00',
                'category_ids': [c1.pk]
            },
            {
                'product_code': 'DUP-1',
                'name': 'Dup2',
                'unit_price': '6.00',
                'category_ids': [c1.pk]
            }
        ]
    }
    with pytest.raises(ValueError):
        product_services.create_products(data, user_id=user.pk)


@pytest.mark.django_db
def test_partial_update_product_happy_and_category_change(user, categories):
    c1, c2 = categories
    # create product manually
    p = Product.objects.create(product_code='PU-1', name='Old',
                               unit_price=Decimal('10.00'), created_by=user, updated_by=user)
    # assign category c1 as primary
    ProductCategory.objects.create(
        product=p, category=c1, is_primary=True, assigned_by=user)

    # update name and unit_price and change categories to [c2]
    update_data = {
        'name': 'NewName',
        'unit_price': '15.00',
        'category_ids': [c2.pk],
        'primary_category_id': c2.pk
    }
    res = product_services.partial_update_product(
        p.pk, update_data, user_id=user.pk)
    assert res['success']
    p.refresh_from_db()
    assert p.name == 'NewName'
    assert p.unit_price == Decimal('15.00')
    assert res['categories_updated'] is True
    # primary category should be c2 now
    assert p.get_primary_category().pk == c2.pk


@pytest.mark.django_db
def test_partial_update_product_invalid_user(user, categories):
    c1, _ = categories
    p = Product.objects.create(product_code='PU-2', name='Prod2',
                               unit_price=Decimal('8.00'), created_by=user, updated_by=user)
    with pytest.raises(ValueError):
        product_services.partial_update_product(
            p.pk, {'name': 'X'}, user_id=999999)


@pytest.mark.django_db
def test_get_product_by_filter_basic(user, categories):
    c1, c2 = categories
    p = Product.objects.create(product_code='F-1', name='FilterMe',
                               unit_price=Decimal('30.00'), created_by=user, updated_by=user)
    ProductCategory.objects.create(
        product=p, category=c1, is_primary=True, assigned_by=user)

    res = product_services.get_product_by_filter(product_code='F-1')
    assert res['success']
    data = res['data']
    # Expect list with product entries
    assert isinstance(data, list)
    assert any(entry['product']['product_code'] == 'F-1' for entry in data)


@pytest.mark.django_db
def test_get_product_by_filter_by_category(user, categories):
    c1, c2 = categories
    p1 = Product.objects.create(product_code='PC-1', name='P1',
                                unit_price=Decimal('10.00'), created_by=user, updated_by=user)
    p2 = Product.objects.create(product_code='PC-2', name='P2',
                                unit_price=Decimal('11.00'), created_by=user, updated_by=user)
    ProductCategory.objects.create(
        product=p1, category=c1, is_primary=True, assigned_by=user)
    ProductCategory.objects.create(
        product=p2, category=c2, is_primary=True, assigned_by=user)

    res = product_services.get_product_by_filter(category_id=c1.pk)
    assert res['success']
    assert any(entry['product']['product_code']
               == 'PC-1' for entry in res['data'])
