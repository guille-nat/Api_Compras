from .models import Installment, Payment
from django.utils import timezone
from decimal import Decimal
from django.db.models import QuerySet
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model


def get_installments_by_id(installment_id: int) -> Installment | None:
    return Installment.objects.filter(id=installment_id).first()


def get_installments_discount(installment: Installment):
    now = timezone.now()
    if installment.due_date > now.date() and installment.state != Installment.State.PAID:
        return Decimal('5.0')
    else:
        return Decimal('0.0')


def calculate_surcharge_over_installments(total_installments_count: int, total_amount: Decimal) -> tuple[bool, Decimal]:
    surcharge = False
    amount = total_amount
    if total_installments_count > 6:
        surcharge = True
        amount += amount * Decimal('15.0') / Decimal('100.0')
    return surcharge, amount


def get_all_payments_by_user(user_id: int) -> QuerySet:
    if not user_id:
        raise ValueError("El user_id es obligatorio.")
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("El user_id debe ser un entero positivo.")

    user_model = get_user_model()
    user = get_object_or_404(user_model, id=user_id)
    return Payment.objects.filter(
        installment__purchase__user_id=user_id
    ).order_by('-payment_date')
