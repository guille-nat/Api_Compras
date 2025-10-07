import pytest
from types import SimpleNamespace
from django.contrib.auth import get_user_model

from api.serializers import NotificationTemplateSerializer
from api.constants import NotificationCodes

User = get_user_model()


@pytest.mark.django_db
def test_notificationtemplate_serializer_create_and_update_sets_audit_fields():
    user = User.objects.create(
        username="ser_user", email="s@example.com", password="pwd")

    data = {
        "code": NotificationCodes.CREATED_ACCOUNT,
        "subject": "Hola",
        "head_html": "<h1>H</h1>",
        "footer_html": "<f/>",
        "active": True,
    }

    serializer = NotificationTemplateSerializer(
        data=data, context={"request": SimpleNamespace(user=user)})
    assert serializer.is_valid(), serializer.errors
    obj = serializer.save()
    assert getattr(obj, 'created_by') == user

    other = User.objects.create(
        username="other", email="o@example.com", password="pwd")
    serializer2 = NotificationTemplateSerializer(obj, data={
                                                 "subject": "nuevo"}, partial=True, context={"request": SimpleNamespace(user=other)})
    assert serializer2.is_valid(), serializer2.errors
    updated = serializer2.save()
    assert getattr(updated, 'updated_by') == other
