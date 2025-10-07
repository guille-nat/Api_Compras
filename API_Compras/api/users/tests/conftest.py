import pytest


@pytest.fixture
def admin(db, django_user_model):
    return django_user_model.objects.create_user(username='adminu', email='admin@example.test', password='pw', is_superuser=True)


@pytest.fixture
def normal_user(db, django_user_model):
    return django_user_model.objects.create_user(username='norm', email='norm@example.test', password='pw')
