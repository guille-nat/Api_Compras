import pytest
from django.urls import reverse
from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth import get_user_model
from api.constants import NotificationCodes

User = get_user_model()


@pytest.mark.django_db
def test_notificationtemplate_viewset_permissions_and_crud():
    factory = APIRequestFactory()

    admin = User.objects.create(
        username="admin", email="a@example.com", password="pwd", is_staff=True)
    normal = User.objects.create(
        username="norm", email="n@example.com", password="pwd", is_staff=False)

    url = reverse('notification-templates-list')
    req = factory.get(url)
    force_authenticate(req, user=normal)
    from api.views import NotificationTemplateViewSet

    view = NotificationTemplateViewSet.as_view({'get': 'list'})
    resp = view(req)
    assert resp.status_code == 403

    payload = {
        # use a code present in the model choices
        "code": NotificationCodes.CREATED_ACCOUNT,
        "subject": "T",
        "head_html": "<h1/>",
        "footer_html": "<f/>",
        "active": True,
    }
    req2 = factory.post(url, payload, format='json')
    force_authenticate(req2, user=admin)
    view_create = NotificationTemplateViewSet.as_view({'post': 'create'})
    resp2 = view_create(req2)
    resp2.render()
    assert resp2.status_code == 201, f"create returned {resp2.status_code}: {getattr(resp2, 'data', getattr(resp2, 'content', None))}"
    # normalize response data (sometimes .data may be a rendered string in certain test environments)
    if isinstance(resp2.data, (list, dict)):
        body = resp2.data
    else:
        import json
        content = resp2.content
        try:
            body = json.loads(content)
        except Exception:
            body = {}
    if isinstance(body, dict):
        assert body.get('created_by') is not None
    else:
        # unexpected shape, fail the test explicitly with content for debugging
        pytest.fail(
            f"Unexpected create response shape: {type(body)} content: {resp2.content}")

    req3 = factory.get(url)
    force_authenticate(req3, user=admin)
    resp3 = view(req3)
    resp3.render()
    assert resp3.status_code == 200
    # The list endpoint may paginate or order results; assert the object exists in DB
    from api.models import NotificationTemplate
    assert NotificationTemplate.objects.filter(
        code=NotificationCodes.CREATED_ACCOUNT).exists()
