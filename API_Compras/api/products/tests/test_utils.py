import pytest


def test_product_data_validator_basic():
    from api.products.utils import ProductDataValidator

    valid = {
        'product_code': 'ABC123',
        'name': 'Prod',
        'brand': 'Brand',
        'model': 'M1',
        'unit_price': '10.00',
        'category_id': 1,
        'user_id': 1,
    }
    assert ProductDataValidator.single_product(valid) is True

    # missing required
    invalid = dict(valid)
    invalid.pop('name')
    assert ProductDataValidator.single_product(invalid) is False


@pytest.mark.django_db
def test_extract_product_codes_with_promotions(category, user):
    from api.products.models import Product, ProductCategory
    from api.promotions.models import Promotion, PromotionScopeProduct
    from api.products.utils import extract_product_codes

    p = Product.objects.create(product_code='AA1', name='X', unit_price='5.00')
    ProductCategory.objects.create(
        product=p, category=category, is_primary=True)

    promo = Promotion.objects.create(name='P1', active=True)
    PromotionScopeProduct.objects.create(product=p, promotion=promo)

    products_qs = Product.objects.filter(id=p.id)
    scopes_qs = PromotionScopeProduct.objects.filter(product=p)

    out = extract_product_codes(products_qs, scopes_qs)
    assert isinstance(out, list)
    assert out[0]['product']['product_code'] == 'AA1'
