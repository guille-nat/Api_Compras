import pytest


@pytest.mark.django_db
def test_location_serializer_create_and_update(admin_user):
    from api.storage_location.serializers import LocationSerializer
    from api.storage_location.models import StorageLocation

    payload = {
        'name': 'Main',
        'street': 'Av X',
        'street_number': '123',
        'floor_unit': '1A',
        'state': 'State',
        'city': 'City',
        'country': 'Country',
        'type': 'WH',
        'parent': None
    }

    ser = LocationSerializer(data=payload, context={
                             'request': type('R', (), {'user': admin_user})})
    assert ser.is_valid(), ser.errors
    obj = ser.save()
    assert obj.created_by == admin_user

    # Update
    upd = LocationSerializer(instance=obj, data={'name': 'Main Updated'}, partial=True, context={
                             'request': type('R', (), {'user': admin_user})})
    assert upd.is_valid(), upd.errors
    obj2 = upd.save()
    assert obj2.updated_by == admin_user


@pytest.mark.django_db
def test_location_viewset_crud(admin_user):
    from rest_framework.test import APIRequestFactory, force_authenticate
    from api.storage_location import views
    from api.storage_location.models import StorageLocation

    factory = APIRequestFactory()

    # Create
    req = factory.post('/api/locations/', {
        'name': 'L1', 'street': 'S', 'street_number': '1', 'state': 'St', 'city': 'C', 'country': 'CO', 'type': 'WH', 'parent': None
    }, format='json')
    force_authenticate(req, user=admin_user)
    resp = views.LocationViewSet.as_view({'post': 'create'})(req)
    # DRF returns 201 on create
    assert resp.status_code in (200, 201)

    # List
    req2 = factory.get('/api/locations/')
    force_authenticate(req2, user=admin_user)
    resp2 = views.LocationViewSet.as_view({'get': 'list'})(req2)
    resp2.render()
    assert resp2.status_code == 200

    # Retrieve
    loc = StorageLocation.objects.first()
    req3 = factory.get(f'/api/locations/{loc.pk}/')
    force_authenticate(req3, user=admin_user)
    resp3 = views.LocationViewSet.as_view({'get': 'retrieve'})(req3, pk=loc.pk)
    resp3.render()
    assert resp3.status_code == 200

    # Update
    req4 = factory.patch(
        f'/api/locations/{loc.pk}/', {'name': 'X'}, format='json')
    force_authenticate(req4, user=admin_user)
    resp4 = views.LocationViewSet.as_view(
        {'patch': 'partial_update'})(req4, pk=loc.pk)
    resp4.render()
    assert resp4.status_code == 200

    # Destroy
    req5 = factory.delete(f'/api/locations/{loc.pk}/')
    force_authenticate(req5, user=admin_user)
    resp5 = views.LocationViewSet.as_view(
        {'delete': 'destroy'})(req5, pk=loc.pk)
    # some DRF versions return 204, some 200 with a body
    assert resp5.status_code in (200, 204)
