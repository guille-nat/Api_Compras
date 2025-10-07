import pytest
from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_list_categories_public_view_returns_data(monkeypatch):
    from api.categories import views

    factory = APIRequestFactory()
    req = factory.get('/api/categories/public')

    # prepare fake queryset/serializer output
    fake_data = [{"id": 1, "name": "PublicCat"}]

    class FakeQS:
        def __iter__(self):
            return iter([])

    # monkeypatch selectors.list_categories_public to return a queryset-like
    monkeypatch.setattr(
        'api.categories.selectors.list_categories_public', lambda: FakeQS())

    # monkeypatch serializer to return our fake_data when passed the fake QS
    # Instead of patching serializer class, we'll call the view and assert structure
    resp = views.list_categories_public(req)

    assert resp.status_code == 200
    # render the DRF Response so .content is available
    resp.render()
    import json
    payload = json.loads(resp.content)
    assert payload["success"] is True
    assert "data" in payload


@pytest.mark.django_db
def test_list_categories_admin_requires_admin_and_returns_list(monkeypatch):
    from api.categories import views
    User = get_user_model()

    factory = APIRequestFactory()
    req = factory.get('/api/categories/admin')

    # Disable user-created signals to avoid external side-effects during user creation
    from django.db.models.signals import post_save
    from api.users.models import CustomUser
    import api.signals as signals

    try:
        post_save.disconnect(
            signals.send_account_created_notification, sender=CustomUser)
    except Exception:
        pass
    try:
        post_save.disconnect(
            signals.send_account_updated_notification, sender=CustomUser)
    except Exception:
        pass

    # create normal and admin user with unique emails to avoid UNIQUE constraint on email
    normal = User.objects.create_user(
        username='normal', password='pw', email='normal@example.test')
    admin = User.objects.create_user(
        username='adm', password='pw', email='adm@example.test', is_staff=True, is_superuser=True)

    # Call with normal user: should be forbidden (403)
    force_authenticate(req, user=normal)
    resp = views.list_categories_admin(req)
    assert resp.status_code == 403

    # Call with admin user
    req2 = factory.get('/api/categories/admin')
    force_authenticate(req2, user=admin)

    # monkeypatch selectors to return empty list
    monkeypatch.setattr(
        'api.categories.selectors.list_categories_admin', lambda: [])

    resp2 = views.list_categories_admin(req2)
    assert resp2.status_code == 200
    # render the DRF Response so .content is available
    resp2.render()
    import json as _json
    payload2 = _json.loads(resp2.content)
    assert payload2["success"] is True
