import pytest
from typing import cast
from django.http import Http404

from api.utils import validate_id, get_notification_by_code
from api.models import NotificationTemplate
from api.constants import NotificationCodes


@pytest.mark.django_db
def test_validate_id_errors_and_ok():
    with pytest.raises(ValueError):
        validate_id(cast(int, None))
    with pytest.raises(ValueError):
        validate_id(-1)
    with pytest.raises(ValueError):
        validate_id(0)
    with pytest.raises(ValueError):
        validate_id(cast(int, "x"))

    # ok
    validate_id(1)


@pytest.mark.django_db
def test_get_notification_by_code_found_and_404():
    tpl = NotificationTemplate.objects.create(
        code=NotificationCodes.INSTALLMENT_PAID,
        subject="Prueba",
        head_html="<h1/>",
        footer_html="<f/>",
        active=True,
    )

    found = get_notification_by_code(NotificationCodes.INSTALLMENT_PAID)
    assert found.pk == tpl.pk

    with pytest.raises(Http404):
        get_notification_by_code("not-real")
