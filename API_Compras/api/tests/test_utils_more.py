import pytest
from typing import cast
from api.utils import validate_id, get_notification_by_code
from api.constants import NotificationCodes
from api.models import NotificationTemplate


def test_validate_id_accepts_positive_int_and_rejects_others():
    validate_id(5)
    with pytest.raises(ValueError):
        validate_id(0)
    with pytest.raises(ValueError):
        validate_id(-10)
    with pytest.raises(ValueError):
        validate_id(cast(int, None))


@pytest.mark.django_db
def test_get_notification_by_code_type_and_not_found():
    # invalid types
    with pytest.raises(ValueError):
        get_notification_by_code(cast(str, None))
    with pytest.raises(ValueError):
        get_notification_by_code(cast(str, 123))

    # create a template and fetch
    tpl = NotificationTemplate.objects.create(
        code=NotificationCodes.PURCHASE_CONFIRMED,
        subject='S', head_html='<h1/>', footer_html='<f/>', active=True)
    found = get_notification_by_code(NotificationCodes.PURCHASE_CONFIRMED)
    assert found.pk == tpl.pk
