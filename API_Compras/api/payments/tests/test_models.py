import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from decimal import Decimal
from django.utils import timezone

from api.payments.models import Installment, Payment
from api.purchases.models import Purchase


User = get_user_model()


@pytest.mark.django_db
def test_installment_creation_and_unique_constraint():
    """Crea cuotas para una compra y verifica la constraint unique en (purchase,num_installment)."""
    user = User.objects.create(
        username="u1", email="u1@example.com", password="pwd")
    purchase = Purchase.objects.create(
        user=user, purchase_date=timezone.now(), total_amount=Decimal('100.00'))

    inst1 = Installment.objects.create(purchase=purchase, num_installment=1, base_amount=Decimal(
        '50.00'), amount_due=Decimal('50.00'), due_date=timezone.now().date())
    assert inst1.pk is not None

    with transaction.atomic():
        with pytest.raises(IntegrityError):
            Installment.objects.create(purchase=purchase, num_installment=1, base_amount=Decimal(
                '50.00'), amount_due=Decimal('50.00'), due_date=timezone.now().date())


@pytest.mark.django_db
def test_payment_creation_and_external_ref_unique():
    """Crea un pago y verifica unique external_ref y defaults de payment_method y ordering."""
    user = User.objects.create(
        username="u2", email="u2@example.com", password="pwd")
    purchase = Purchase.objects.create(
        user=user, purchase_date=timezone.now(), total_amount=Decimal('200.00'))
    inst = Installment.objects.create(purchase=purchase, num_installment=1, base_amount=Decimal(
        '200.00'), amount_due=Decimal('200.00'), due_date=timezone.now().date())

    pay1 = Payment.objects.create(
        installment=inst, amount=Decimal('200.00'), external_ref="REF123")
    assert pay1.pk is not None
    assert pay1.payment_method == Payment.Method.CASH

    with transaction.atomic():
        with pytest.raises(IntegrityError):
            Payment.objects.create(installment=inst, amount=Decimal(
                '200.00'), external_ref="REF123")

    # ordering verified by creating another payment and checking queryset order
    pay2 = Payment.objects.create(installment=inst, amount=Decimal('100.00'))
    payments = list(Payment.objects.filter(installment=inst))
    # ordering = ['-payment_date'] so the most recent (pay2) should come first
    assert payments[0].pk == pay2.pk
