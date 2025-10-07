"""Tests for Product serializers and the products listing view.

These tests are intentionally small and focused:
- verify serializer output shape and key values
- verify the public view behaves correctly on success and error

They use fixtures provided by the test-suite (e.g. `category`, `user`) and
are written to produce clear failure messages for debugging.
"""

from decimal import Decimal
import json
import pytest

from rest_framework import status


@pytest.mark.django_db
def test_product_serializer_and_basic(category):
    """ProductSerializer and ProductBasicSerializer should include primary_category

    The test creates a Product and a ProductCategory marked as primary and
    asserts that both serializers expose the primary category information.
    """
    from api.products.models import Product, ProductCategory
    from api.products.serializers import ProductSerializer, ProductBasicSerializer

    # Create product; use Decimal-compatible string to ensure serializer casts
    p = Product.objects.create(
        product_code="PC1", name="Name", unit_price="12.00")

    # Link the product to the provided category fixture and mark as primary
    pc = ProductCategory.objects.create(
        product=p, category=category, is_primary=True)

    # Full serializer should include product_code and nested primary_category
    ser = ProductSerializer(instance=p)
    data = ser.data
    assert data.get(
        "product_code") == "PC1", f"unexpected product_code: {data.get('product_code')!r}"
    assert "primary_category" in data, "ProductSerializer must include 'primary_category'"
    assert data["primary_category"]["id"] == pc.id, "primary_category id must match the created ProductCategory"

    # Basic serializer should also include primary_category but with minimal fields
    basic = ProductBasicSerializer(instance=p)
    bdata = basic.data
    assert "primary_category" in bdata, "ProductBasicSerializer must include 'primary_category'"
    # unit_price should be serializable to Decimal-like string
    assert Decimal(bdata.get("unit_price")) == Decimal("12.00")


def test_get_products_view_success_and_error(monkeypatch):
    """The products view should return the service response on success and
    handle errors from the service gracefully.
    """
    from rest_framework.test import APIRequestFactory
    from api.products import views

    fake_response = {"success": True, "message": "ok", "data": []}

    # Patch the service used by the view (prefer direct attribute patching)
    monkeypatch.setattr(
        views, "get_all_products_with_promotions", lambda **kwargs: fake_response)

    factory = APIRequestFactory()
    req = factory.get("/api/products")
    resp = views.get_products(req)
    # Ensure DRF has rendered the Response.data property
    resp.render()
    assert resp.status_code == status.HTTP_200_OK, f"expected 200, got {resp.status_code}"
    assert isinstance(resp.data, dict) and resp.data.get("success") is True

    # Now simulate the service raising an exception and verify the view returns 500
    def raising_service(**kwargs):
        raise RuntimeError("service failure")

    monkeypatch.setattr(
        views, "get_all_products_with_promotions", raising_service)
    resp2 = views.get_products(req)
    resp2.render()
    assert resp2.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR, (
        "When the product service raises, the view should return 500")
    # response body should be JSON with success=False
    try:
        body = resp2.data
    except Exception:
        # Fallback: parse raw content if DRF didn't populate .data
        body = json.loads(resp2.content.decode("utf-8"))
    assert body.get(
        "success") is False, "Error responses from view should include success=False"
