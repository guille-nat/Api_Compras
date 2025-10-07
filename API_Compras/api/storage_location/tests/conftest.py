import pytest


@pytest.fixture
def admin_user(db, django_user_model):
    return django_user_model.objects.create_user(username='adminloc', email='adminloc@example.test', password='pw', is_staff=True, is_superuser=True)
