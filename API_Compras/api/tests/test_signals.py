import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from api.models import NotificationTemplate, NotificationLog
from api.constants import NotificationCodes

User = get_user_model()


@pytest.mark.django_db
def test_send_installment_payment_signal_creates_log_and_calls_sendemail(monkeypatch):
    user = User.objects.create(
        username="siguser", email="s2@example.com", password="pwd")
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

    NotificationTemplate.objects.create(
        code=NotificationCodes.INSTALLMENT_PAID,
        subject="Cuota pagada",
        head_html="<h1/>",
        footer_html="<f/>",
        active=True,
    )

    called = {'n': 0}

    def fake_send_email_task(email, template_id, context, log_email_id):
        """Simula ejecución síncrona de la tarea Celery"""
        called['n'] += 1
        # Simular que la tarea se ejecutó y marcó como SENT
        if log_email_id:
            log = NotificationLog.objects.get(id=log_email_id)
            log.status = NotificationLog.Status.SENT
            log.sent_at = timezone.now()
            log.save()

    import importlib
    tasks_mod = importlib.import_module('api.tasks')

    # Mock del método delay para que ejecute síncronamente
    original_task = tasks_mod.send_email_task
    monkeypatch.setattr(original_task, 'delay', fake_send_email_task)

    inst.state = Installment.State.PAID
    inst.save()

    nl = NotificationLog.objects.filter(
        user=user, template__code=NotificationCodes.INSTALLMENT_PAID).first()
    assert nl is not None
    assert nl.status == NotificationLog.Status.SENT
    assert called['n'] == 1
