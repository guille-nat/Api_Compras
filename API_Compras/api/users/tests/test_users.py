import pytest


def test_user_serializer_create(db):
    from api.users.serializers import UserSerializer

    payload = {
        'username': 'u1',
        'email': 'u1@example.com',
        'password': 'secret'
    }
    ser = UserSerializer(data=payload)
    assert ser.is_valid(), ser.errors
    user = ser.save()
    assert user.username == 'u1'


@pytest.mark.django_db
def test_user_delete_permissions(admin, normal_user):
    from rest_framework.test import APIRequestFactory, force_authenticate
    from api.users import view

    factory = APIRequestFactory()

    # normal user attempting to delete someone else -> 403
    req = factory.delete(f'/api/users/{admin.pk}/')
    force_authenticate(req, user=normal_user)
    resp = view.UserViewSet.as_view({'delete': 'destroy'})(req, pk=admin.pk)
    assert resp.status_code == 403

    # admin deleting normal user -> 200
    req2 = factory.delete(f'/api/users/{normal_user.pk}/')
    force_authenticate(req2, user=admin)
    resp2 = view.UserViewSet.as_view(
        {'delete': 'destroy'})(req2, pk=normal_user.pk)
    assert resp2.status_code in (200, 204)

    # admin cannot delete self
    req3 = factory.delete(f'/api/users/{admin.pk}/')
    force_authenticate(req3, user=admin)
    resp3 = view.UserViewSet.as_view({'delete': 'destroy'})(req3, pk=admin.pk)
    assert resp3.status_code == 403
