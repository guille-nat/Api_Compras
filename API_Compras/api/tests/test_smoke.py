import pytest
from django.urls import reverse, resolve
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_django_arranca_y_root_url_resuelve():
    # Cambia 'admin:index' por alguna ruta segura de tu proyecto si querés
    match = resolve("/admin/login/")
    assert match is not None


def test_auth_required_por_defecto():
    client = APIClient()
    # Cambiá por un endpoint real que tengas protegido (ej: /api/purchases)
    resp = client.get("/api/v2/purchases")
    assert resp.status_code in (401, 403)
