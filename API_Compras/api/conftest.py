import pytest
from django.contrib.auth import get_user_model
from decimal import Decimal


@pytest.fixture
def user(db):
    """Create and return a default test user."""
    User = get_user_model()
    return User.objects.create_user(username="testuser", email="test@example.com", password="pwd")


@pytest.fixture
def product_factory(db):
    """Simple product factory for tests.

    Returns a callable that creates a Product with given params and sets a
    dynamic `stock` attribute so tests can monkeypatch or inspect it.
    """
    from api.products.models import Product

    def _create(code="P001", name="Prod", price="10.00", stock=100):
        p = Product.objects.create(
            product_code=code, name=name, unit_price=Decimal(price))
        # attach dynamic attribute for tests; model may not have DB field
        setattr(p, "stock", stock)
        return p

    return _create
