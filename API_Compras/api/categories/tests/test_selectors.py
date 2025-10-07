import pytest


@pytest.mark.django_db
def test_list_categories_public_returns_all(db, django_user_model):
    from api.categories.selectors import list_categories_public
    from api.categories.models import Category

    # create some categories
    Category.objects.create(name="Alpha")
    Category.objects.create(name="Beta")

    qs = list_categories_public()

    # should be a queryset and contain two items
    assert qs.count() == 2
    names = [c.name for c in qs]
    assert set(names) == {"Alpha", "Beta"}


@pytest.mark.django_db
def test_list_categories_admin_includes_user_fields(db, django_user_model):
    from api.categories.selectors import list_categories_admin
    from api.categories.models import Category

    User = django_user_model
    user = User.objects.create_user(username="u1", password="pw")

    cat = Category.objects.create(
        name="Gamma", created_by=user, updated_by=user)

    qs = list_categories_admin()

    # ensure our created category is present and related fields are accessible
    assert any(c.pk == cat.pk for c in qs)
    # accessing related attributes should not raise
    found = [c for c in qs if c.pk == cat.pk][0]
    assert found.created_by_id == user.id
