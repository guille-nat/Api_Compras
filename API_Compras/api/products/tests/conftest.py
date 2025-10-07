import pytest


@pytest.fixture
def user(db, django_user_model):
    return django_user_model.objects.create_user(username='produser', email='prod@example.test', password='pw')


@pytest.fixture
def category(db):
    from api.categories.models import Category
    return Category.objects.create(name='Cat1')
