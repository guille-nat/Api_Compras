import pytest
from django.urls import reverse
from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth import get_user_model
from api.constants import NotificationCodes
from api.models import NotificationTemplate

User = get_user_model()


@pytest.mark.django_db
def test_notificationtemplate_retrieve_update_partial_destroy():
    factory = APIRequestFactory()
    admin = User.objects.create(
        username='adm2', email='a2@example.com', password='pwd', is_staff=True)

    # create a template directly
    tpl = NotificationTemplate.objects.create(
        code=NotificationCodes.CREATED_ACCOUNT,
        subject='S1',
        head_html='<h1/>',
        footer_html='<f/>',
        active=True,
    )

    detail_url = reverse('notification-templates-detail',
                         kwargs={'pk': tpl.pk})

    # retrieve
    req = factory.get(detail_url)
    force_authenticate(req, user=admin)
    from api.views import NotificationTemplateViewSet
    view_retrieve = NotificationTemplateViewSet.as_view({'get': 'retrieve'})
    resp = view_retrieve(req, pk=tpl.pk)
    resp.render()
    assert resp.status_code == 200
    assert resp.data.get('code') == NotificationCodes.CREATED_ACCOUNT

    # full update (put)
    payload = {
        'code': tpl.code,
        'subject': 'S-updated',
        'head_html': '<h2/>',
        'footer_html': '<f2/>',
        'active': False,
    }
    req2 = factory.put(detail_url, payload, format='json')
    force_authenticate(req2, user=admin)
    view_update = NotificationTemplateViewSet.as_view({'put': 'update'})
    resp2 = view_update(req2, pk=tpl.pk)
    resp2.render()
    assert resp2.status_code == 200
    tpl.refresh_from_db()
    assert tpl.subject == 'S-updated'
    assert tpl.active is False

    # partial update (patch)
    payload2 = {'subject': 'S-patched'}
    req3 = factory.patch(detail_url, payload2, format='json')
    force_authenticate(req3, user=admin)
    view_patch = NotificationTemplateViewSet.as_view(
        {'patch': 'partial_update'})
    resp3 = view_patch(req3, pk=tpl.pk)
    resp3.render()
    assert resp3.status_code == 200
    tpl.refresh_from_db()
    assert tpl.subject == 'S-patched'

    # destroy
    req4 = factory.delete(detail_url)
    force_authenticate(req4, user=admin)
    view_destroy = NotificationTemplateViewSet.as_view({'delete': 'destroy'})
    resp4 = view_destroy(req4, pk=tpl.pk)
    # allow 204 or 200 depending on DRF version/config
    assert resp4.status_code in (200, 204)
    assert not NotificationTemplate.objects.filter(pk=tpl.pk).exists()


@pytest.mark.django_db
def test_non_admin_cannot_destroy_template():
    factory = APIRequestFactory()
    admin = User.objects.create(
        username='adm3', email='a3@example.com', password='pwd', is_staff=True)
    normal = User.objects.create(
        username='u3', email='u3@example.com', password='pwd', is_staff=False)

    tpl = NotificationTemplate.objects.create(
        code=NotificationCodes.INSTALLMENT_PAID,
        subject='S2',
        head_html='<h1/>',
        footer_html='<f/>',
        active=True,
    )

    detail_url = reverse('notification-templates-detail',
                         kwargs={'pk': tpl.pk})
    req = factory.delete(detail_url)
    force_authenticate(req, user=normal)
    from api.views import NotificationTemplateViewSet
    resp = NotificationTemplateViewSet.as_view(
        {'delete': 'destroy'})(req, pk=tpl.pk)
    assert resp.status_code == 403
    # cleanup
    NotificationTemplate.objects.filter(pk=tpl.pk).delete()
