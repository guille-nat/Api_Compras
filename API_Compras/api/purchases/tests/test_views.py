"""Tests for purchases.views endpoints.

These tests monkeypatch the service layer functions used by the views so the
tests remain fast and focused on the view layer behavior (status codes,
input validation and error handling).
"""
import pytest
from typing import cast
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from rest_framework.response import Response as DRFResponse
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_update_purchase_status_ok_and_bad_request(monkeypatch):
    from api.purchases import views

    factory = APIRequestFactory()
    user = User.objects.create_user(
        username="u1", email="u1@example.com", password="pwd")

    # Successful service response
    def fake_service(purchase_id, new_status, user_id, reason=None):
        return {"success": True, "message": "updated", "data": {"id": int(purchase_id), "status": new_status}}

    monkeypatch.setattr(views, "service_update_purchase_status", fake_service)

    req = factory.patch("/purchases/1/status",
                        {"new_status": "PAID"}, format='json')
    force_authenticate(req, user=user)
    resp = views.update_purchase_status(req, purchase_id=1)
    resp = cast(DRFResponse, resp)
    resp.render()
    assert resp.status_code == status.HTTP_200_OK
    data = cast(dict, resp.data)
    assert data.get("success") is True

    # Missing new_status -> bad request
    req2 = factory.patch("/purchases/1/status", {}, format='json')
    force_authenticate(req2, user=user)
    resp2 = views.update_purchase_status(req2, purchase_id=1)
    resp2 = cast(DRFResponse, resp2)
    resp2.render()
    assert resp2.status_code == status.HTTP_400_BAD_REQUEST
    data2 = cast(dict, resp2.data)
    assert data2.get("success") is False or data2.get("message") is not None


@pytest.mark.django_db
def test_update_purchase_installments_ok_and_invalid_int(monkeypatch):
    from api.purchases import views

    factory = APIRequestFactory()
    user = User.objects.create_user(
        username="u2", email="u2@example.com", password="pwd")

    def fake_service(purchase_id, new_installments_count, user_id, reason=None):
        return {"success": True, "message": "installments updated"}

    monkeypatch.setattr(
        views, "service_update_purchase_installments", fake_service)

    req = factory.patch("/purchases/1/installments",
                        {"new_installments_count": 6}, format='json')
    force_authenticate(req, user=user)
    resp = views.update_purchase_installments(req, purchase_id=1)
    resp = cast(DRFResponse, resp)
    resp.render()
    assert resp.status_code == status.HTTP_200_OK
    data3 = cast(dict, resp.data)
    assert data3.get("success") is True

    # invalid integer
    req2 = factory.patch("/purchases/1/installments",
                         {"new_installments_count": "notint"}, format='json')
    force_authenticate(req2, user=user)
    resp2 = views.update_purchase_installments(req2, purchase_id=1)
    resp2 = cast(DRFResponse, resp2)
    resp2.render()
    assert resp2.status_code == status.HTTP_400_BAD_REQUEST
    data4 = cast(dict, resp2.data)
    assert data4.get("success") is False


@pytest.mark.django_db
def test_update_purchase_discount_and_admin_delete(monkeypatch):
    from api.purchases import views

    factory = APIRequestFactory()
    user = User.objects.create_user(
        username="u3", email="u3@example.com", password="pwd")

    def fake_discount(purchase_id, new_discount, user_id, reason=None):
        return {"success": True, "message": "discount updated"}

    monkeypatch.setattr(
        views, "service_update_purchase_discount", fake_discount)

    req = factory.patch("/purchases/1/discount",
                        {"new_discount": "5.00"}, format='json')
    force_authenticate(req, user=user)
    resp = views.update_purchase_discount(req, purchase_id=1)
    resp = cast(DRFResponse, resp)
    resp.render()
    assert resp.status_code == status.HTTP_200_OK
    data5 = cast(dict, resp.data)
    assert data5.get("success") is True

    # admin delete: patch delete_purchase_admin
    admin = User.objects.create_superuser(
        username="admin", email="a@example.com", password="pwd")

    def fake_delete(purchase_id, admin_user_id, force_delete=False):
        return {"success": True, "message": "deleted"}

    monkeypatch.setattr(views, "delete_purchase_admin", fake_delete)
    req2 = factory.delete("/purchases/1", {})
    force_authenticate(req2, user=admin)
    resp2 = views.admin_delete_purchase(req2, purchase_id=1)
    resp2 = cast(DRFResponse, resp2)
    resp2.render()
    assert resp2.status_code == status.HTTP_200_OK
    data6 = cast(dict, resp2.data)
    assert data6.get("success") is True
