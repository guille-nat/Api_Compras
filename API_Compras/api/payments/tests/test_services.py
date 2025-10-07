import pytest
from decimal import Decimal
from datetime import datetime, timedelta, date
from django.core import exceptions
from django.utils import timezone
from api.payments import services as payment_services
from api.payments.models import Installment, Payment, InstallmentAuditLog
from api.purchases.models import Purchase
from api.users.models import CustomUser


@pytest.fixture
def user(db):
    return CustomUser.objects.create(username="svc_user", email="svc@example.com", password="pwd")


@pytest.fixture
def purchase(db, user):
    return Purchase.objects.create(user=user, purchase_date=timezone.now(), total_amount=Decimal('120.00'), total_installments_count=3)


@pytest.mark.django_db
def test_create_installments_for_purchase_happy(purchase):
    res = payment_services.create_installments_for_purchase(purchase.pk)
    assert res['success']
    assert res['data']['installments_created'] == 3
    # Verify DB rows
    assert Installment.objects.filter(purchase=purchase).count() == 3


@pytest.mark.django_db
def test_create_installments_invalid_purchase():
    with pytest.raises(exceptions.ValidationError):
        payment_services.create_installments_for_purchase(999999)


@pytest.mark.django_db
def test_pay_installment_happy_and_insufficient(purchase, user):
    # create one installment
    inst = Installment.objects.create(
        purchase=purchase,
        num_installment=1,
        base_amount=Decimal('40.00'),
        surcharge_pct=Decimal('0.0'),
        discount_pct=Decimal('0.0'),
        amount_due=Decimal('40.00'),
        due_date=date.today(),
        state=Installment.State.PENDING,
    )

    # insufficient amount
    with pytest.raises(exceptions.ValidationError):
        payment_services.pay_installment(
            inst.pk, Decimal('10.00'), 'CARD', None)

    # sufficient amount
    res = payment_services.pay_installment(
        inst.pk, Decimal('40.00'), 'CARD', 'EXT-1')
    assert res['success']
    inst.refresh_from_db()
    assert inst.state == Installment.State.PAID
    # Payment created
    p = Payment.objects.filter(installment=inst, external_ref='EXT-1').first()
    assert p is not None


@pytest.mark.django_db
def test_auto_update_overdue_and_surcharge(user):
    # installment pending and due yesterday -> should become overdue
    purch = Purchase.objects.create(user=user, purchase_date=timezone.now(
    ) - timedelta(days=60), total_amount=Decimal('50.00'))
    inst1 = Installment.objects.create(purchase=purch, num_installment=1, base_amount=Decimal('50.00'), surcharge_pct=Decimal('0.0'), discount_pct=Decimal(
        '0.0'), amount_due=Decimal('50.00'), due_date=(timezone.now().date() - timedelta(days=1)), state=Installment.State.PENDING)

    # installment overdue exactly 7 days ago -> will get surcharge when auto_update_surcharge_late_installments runs
    inst2 = Installment.objects.create(purchase=purch, num_installment=2, base_amount=Decimal('50.00'), surcharge_pct=Decimal('0.0'), discount_pct=Decimal(
        '0.0'), amount_due=Decimal('50.00'), due_date=(timezone.now().date() - timedelta(days=7)), state=Installment.State.OVERDUE)

    res1 = payment_services.auto_update_overdue_installments()
    assert res1['success']
    # inst1 should now be OVERDUE
    inst1.refresh_from_db()
    assert inst1.state == Installment.State.OVERDUE

    # apply surcharge to inst2 (due exactly 7 days ago)
    res2 = payment_services.auto_update_surcharge_late_installments()
    assert res2['success']
    inst2.refresh_from_db()
    # ensure we compare Decimal values to avoid type-checker complaints
    assert Decimal(inst2.surcharge_pct) >= Decimal('8.0')


@pytest.mark.django_db
def test_update_state_paid_purchase_and_delete(purchase, user):
    # create two installments, mark both paid to cause purchase to be marked as PAID
    i1 = Installment.objects.create(purchase=purchase, num_installment=1, base_amount=Decimal('60.00'), surcharge_pct=Decimal(
        '0.0'), discount_pct=Decimal('0.0'), amount_due=Decimal('60.00'), due_date=date.today(), state=Installment.State.PAID)
    i2 = Installment.objects.create(purchase=purchase, num_installment=2, base_amount=Decimal('60.00'), surcharge_pct=Decimal(
        '0.0'), discount_pct=Decimal('0.0'), amount_due=Decimal('60.00'), due_date=date.today(), state=Installment.State.PAID)

    res = payment_services.update_state_paid_purchase(purchase)
    assert res['success']
    purchase.refresh_from_db()
    assert purchase.status == Purchase.Status.PAID

    # delete one installment via service
    # create a fresh installment to delete
    inst_del = Installment.objects.create(purchase=purchase, num_installment=3, base_amount=Decimal('10.00'), surcharge_pct=Decimal(
        '0.0'), discount_pct=Decimal('0.0'), amount_due=Decimal('10.00'), due_date=date.today(), state=Installment.State.PENDING)
    res_del = payment_services.delete_installments_by_id(inst_del.pk, user.pk)
    assert res_del['success']
    with pytest.raises(Installment.DoesNotExist):
        Installment.objects.get(pk=inst_del.pk)


@pytest.mark.django_db
def test_update_state_installment_and_audit(purchase, user):
    inst = Installment.objects.create(purchase=purchase, num_installment=1, base_amount=Decimal('40.00'), surcharge_pct=Decimal(
        '0.0'), discount_pct=Decimal('0.0'), amount_due=Decimal('40.00'), due_date=date.today(), state=Installment.State.PENDING)

    res = payment_services.update_state_installment(inst.pk, 'PAID', user)
    assert res['success']
    inst.refresh_from_db()
    assert inst.state == Installment.State.PAID
    # verify audit log entry
    assert InstallmentAuditLog.objects.filter(installment=inst).exists()

    # attempt invalid transition from PAID -> PENDING
    with pytest.raises(exceptions.ValidationError):
        payment_services.update_state_installment(inst.pk, 'PENDING', user)
