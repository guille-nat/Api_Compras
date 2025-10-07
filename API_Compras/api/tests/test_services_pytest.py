import pytest
from django.contrib.auth import get_user_model
from api.models import NotificationTemplate, NotificationLog
from api.constants import NotificationCodes
from api import services as api_services
from django.utils import timezone

User = get_user_model()


@pytest.mark.django_db
def test_defined_message_html_invalid_inputs():
    tpl = NotificationTemplate(
        code=NotificationCodes.PURCHASE_CONFIRMED,
        subject="X",
        head_html="<h1>H</h1>",
        footer_html="<f/>",
    )

    with pytest.raises(ValueError):
        api_services.defined_message_html(None, {})

    with pytest.raises(ValueError):
        api_services.defined_message_html(tpl, None)


@pytest.mark.django_db
def test_defined_message_html_purchase_missing_and_products_empty():
    """If purchase not found, content should include a fallback and products list should show not found message."""
    tpl = NotificationTemplate.objects.create(
        code=NotificationCodes.PURCHASE_CONFIRMED,
        subject="Compra confirmada",
        head_html="<head></head>",
        footer_html="<footer></footer>",
    )

    ctx = {
        "purchase_id": 99999,
        "purchase_date": timezone.now().date().isoformat(),
        "user_full_name": "N/A",
        "installment_number": 1,
        "amount_due": "100.00",
        "installment_due_date": timezone.now().date().isoformat(),
    }

    result = api_services.defined_message_html(tpl, ctx)
    assert "No se encontraron productos" in result or "No hay productos" in result
    assert tpl.subject in result


@pytest.mark.django_db
def test_send_installment_mora_notification_creates_log_and_marks_sent(monkeypatch):
    # create user, purchase and installment minimal objects via models to satisfy relations
    user = User.objects.create(
        username="mailuser", email="m@example.com", password="pwd")

    # create minimal models via imports to avoid circular heavy imports
    from api.purchases.models import Purchase
    from api.payments.models import Installment

    purchase = Purchase.objects.create(
        user=user, purchase_date=timezone.now(), total_installments_count=1)

    inst = Installment.objects.create(
        purchase=purchase,
        num_installment=1,
        base_amount=100,
        amount_due=100,
        due_date=timezone.now().date(),
    )

    # create a template to be found by get_notification_by_code
    tpl = NotificationTemplate.objects.create(
        code=NotificationCodes.OVERDUE_SURCHARGE_NOTICE,
        subject="Mora",
        head_html="<h1/>",
        footer_html="<f/>",
    )

    # monkeypatch sendEmail to avoid real email
    called = {"count": 0}

    def fake_send_email_task(email, template_id, context, log_email_id):
        """Simula ejecución síncrona de la tarea Celery"""
        called["count"] += 1
        # Simular que la tarea se ejecutó y marcó como SENT
        if log_email_id:
            log = NotificationLog.objects.get(id=log_email_id)
            log.status = NotificationLog.Status.SENT
            log.sent_at = timezone.now()
            log.save()

    import importlib
    tasks_mod = importlib.import_module("api.tasks")

    # Mock del método delay para que ejecute síncronamente
    original_task = tasks_mod.send_email_task
    monkeypatch.setattr(original_task, "delay", fake_send_email_task)

    # run
    api_services.send_installment_mora_notification(inst)

    # assert NotificationLog created
    nl = NotificationLog.objects.filter(
        user=user, template__code=NotificationCodes.OVERDUE_SURCHARGE_NOTICE).first()
    assert nl is not None
    assert nl.status == NotificationLog.Status.SENT
    # sent_at should be set
    assert nl.sent_at is not None
    # our fake sendEmail was called
    assert called["count"] == 1
