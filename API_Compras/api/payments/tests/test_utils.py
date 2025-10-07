import pytest


@pytest.mark.django_db
def test_calculate_surcharge_over_installments():
    from decimal import Decimal
    from api.payments.utils import calculate_surcharge_over_installments

    # No surcharge for <= 6 installments
    surcharge, amount = calculate_surcharge_over_installments(
        6, Decimal('100.00'))
    assert surcharge is False
    assert amount == Decimal('100.00')

    # Surcharge applied for > 6 installments (15%)
    surcharge2, amount2 = calculate_surcharge_over_installments(
        7, Decimal('200.00'))
    assert surcharge2 is True
    assert amount2 == Decimal('230.00')  # 200 + 15%


@pytest.mark.django_db
def test_get_installments_discount():
    from django.utils import timezone
    from datetime import timedelta
    from api.payments.utils import get_installments_discount
    from api.payments.models import Installment
    from django.contrib.auth import get_user_model
    from api.purchases.models import Purchase

    User = get_user_model()
    user = User.objects.create_user(
        username='payuser', password='pw', email='pay@example.test')
    purchase = Purchase.objects.create(user=user, purchase_date=timezone.now())

    # installment due in future and not paid -> discount 5.0
    future = timezone.now().date() + timedelta(days=5)
    inst = Installment.objects.create(
        purchase=purchase, num_installment=1, base_amount='100.00', amount_due='100.00', due_date=future)
    from decimal import Decimal
    disc = get_installments_discount(inst)
    assert disc == Decimal('5.0')

    # installment with PAID state -> discount 0.0
    inst_paid = Installment.objects.create(purchase=purchase, num_installment=2, base_amount='50.00',
                                           amount_due='50.00', due_date=future, state=Installment.State.PAID)
    disc2 = get_installments_discount(inst_paid)
    assert disc2 == Decimal('0.0')


@pytest.mark.django_db
def test_get_all_payments_by_user_validation_and_success():
    from api.payments.utils import get_all_payments_by_user
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from api.purchases.models import Purchase
    from api.payments.models import Installment, Payment

    # invalid inputs
    with pytest.raises(ValueError):
        get_all_payments_by_user(None)

    with pytest.raises(ValueError):
        get_all_payments_by_user(-1)

    # valid path: create user, purchase, installment, payment
    User = get_user_model()
    user = User.objects.create_user(
        username='payer', password='pw', email='payer@example.test')
    purchase = Purchase.objects.create(user=user, purchase_date=timezone.now())
    inst = Installment.objects.create(
        purchase=purchase, num_installment=1, base_amount='10.00', amount_due='10.00')
    Payment.objects.create(
        installment=inst, amount='10.00', payment_method='CASH')

    qs = get_all_payments_by_user(user.id)
    assert qs.exists()
