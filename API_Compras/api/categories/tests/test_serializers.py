import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from api.categories.models import Category
from api.categories.serializers import CategoryPrivateSerializer, CategoryPublicSerializer

User = get_user_model()


@pytest.mark.django_db
def test_category_private_serializer_fields_and_readonly():
    user = User.objects.create_user('ser1', 's1@example.com', 'pass')
    cat = Category.objects.create(
        name='  Food  ', created_by=user, updated_by=user)

    ser = CategoryPrivateSerializer(cat)
    data = ser.data

    # fields present
    assert 'id' in data
    assert data['name'] == '  Food  '
    assert 'created_by' in data and data['created_by'] is not None
    assert 'created_at' in data and 'updated_at' in data

    # read_only fields should be ignored when updating via serializer
    other_user = User.objects.create_user('other', 'other@example.com', 'pass')
    input_payload = {'name': 'New Name', 'created_by': other_user.pk}
    ser2 = CategoryPrivateSerializer(
        instance=cat, data=input_payload, partial=True)
    assert ser2.is_valid(), ser2.errors
    updated = ser2.save()
    # name updated, but created_by should remain the original user
    assert updated.name == 'New Name'
    assert updated.created_by == user


@pytest.mark.django_db
def test_validate_name_trims_and_enforces_min_length():
    # name shorter than 2 after trim -> invalid
    s = CategoryPrivateSerializer(data={'name': ' a '})
    assert not s.is_valid()
    assert 'El nombre es demasiado corto.' in str(s.errors['name'][0])

    # valid name is trimmed
    s2 = CategoryPrivateSerializer(data={'name': '  Verduras  '})
    assert s2.is_valid(), s2.errors
    obj = s2.save()
    assert obj.name == 'Verduras'


@pytest.mark.django_db
def test_public_serializer_only_exposes_id_and_name():
    user = User.objects.create_user('ser2', 's2@example.com', 'pass')
    cat = Category.objects.create(name='Bebidas', created_by=user)
    ser = CategoryPublicSerializer(cat)
    data = ser.data
    assert set(data.keys()) == {'id', 'name'}
    assert data['name'] == 'Bebidas'
