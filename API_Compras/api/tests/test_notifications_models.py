import pytest
from django.contrib.auth import get_user_model
from api.constants import NotificationCodes, EmailSettings
from api.models import NotificationTemplate, NotificationLog
from django.utils import timezone

User = get_user_model()


@pytest.mark.django_db
def test_notification_template_creation_and_str_and_unique_code():
    """Crear NotificationTemplate y verificar __str__ y unique code."""
    tpl = NotificationTemplate.objects.create(
        code=NotificationCodes.PURCHASE_CONFIRMED,
        subject="Tu compra fue registrada",
        head_html="<h1>Hola</h1>",
        footer_html="<footer></footer>",
        active=True
    )
    assert tpl.pk is not None
    # __str__ utiliza label del choice
    assert NotificationCodes.PURCHASE_CONFIRMED in str(tpl)

    # unique constraint
    with pytest.raises(Exception):
        NotificationTemplate.objects.create(
            code=NotificationCodes.PURCHASE_CONFIRMED,
            subject="Otro",
            head_html="<h1>1</h1>",
            footer_html="<footer></footer>",
        )


@pytest.mark.django_db
def test_notification_log_template_fk_and_status_and_delete_template_nulls_field():
    """Verificar que NotificationLog referencia template por code (to_field) y que al borrar template el campo se pone a NULL."""
    user = User.objects.create(
        username="notifuser", email="not@ex.com", password="pwd")
    tpl = NotificationTemplate.objects.create(
        code=NotificationCodes.INSTALLMENT_PAID,
        subject="Cuota pagada",
        head_html="<h1>OK</h1>",
        footer_html="<footer></footer>",
    )

    nl = NotificationLog.objects.create(
        user=user,
        template=tpl,
        context_json={"a": 1},
        recipient_email="dest@example.com",
        status=NotificationLog.Status.SENT
    )
    assert nl.pk is not None
    assert nl.template is not None
    assert nl.template.code == tpl.code
    assert nl.status == NotificationLog.Status.SENT

    # al borrar el template, el campo template debe tomar NULL según on_delete=SET_NULL
    tpl.delete()
    nl.refresh_from_db()
    assert nl.template is None
