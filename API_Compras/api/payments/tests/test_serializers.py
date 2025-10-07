from api.users.models import CustomUser
from api.purchases.models import Purchase
from api.payments.models import Installment, Payment
from api.payments.serializers import (
    InstallmentSerializer, InstallmentInformationSerializer, PaymentSerializer
)
from django.db import IntegrityError
from django.utils import timezone
from datetime import date
from decimal import Decimal
import pytest


@pytest.mark.django_db
def test_installment_serializer_fields():
    from api.payments.serializers import InstallmentSerializer
    from api.payments.models import Installment
    from django.utils import timezone
    from api.purchases.models import Purchase
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username='suser', password='pw', email='suser@example.test')
    purchase = Purchase.objects.create(user=user, purchase_date=timezone.now())
    inst = Installment.objects.create(
        purchase=purchase, num_installment=1, base_amount='5.00', amount_due='5.00')

    ser = InstallmentSerializer(instance=inst)
    data = ser.data
    assert 'id' in data
    assert 'amount_due' in data


@pytest.mark.django_db
def test_payment_serializer_roundtrip():
    from api.payments.serializers import PaymentSerializer
    from api.payments.models import Payment, Installment
    from api.purchases.models import Purchase
    from django.utils import timezone
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username='puser', password='pw', email='puser@example.test')
    purchase = Purchase.objects.create(user=user, purchase_date=timezone.now())
    inst = Installment.objects.create(
        purchase=purchase, num_installment=1, base_amount='20.00', amount_due='20.00')
    p = Payment.objects.create(
        installment=inst, amount='20.00', payment_method='CASH')

    ser = PaymentSerializer(instance=p)
    data = ser.data
    assert data['amount'] == '20.00'


@pytest.fixture
def user(db):
    return CustomUser.objects.create(username="u1", email="u1@example.com", password="pwd")


@pytest.fixture
def purchase(db, user):
    return Purchase.objects.create(user=user, purchase_date=timezone.now(), total_amount=Decimal('100.00'))


@pytest.mark.django_db
def test_installment_serializer_happy_path(purchase, user):
    inst = Installment.objects.create(
        purchase=purchase,
        num_installment=1,
        base_amount=Decimal('50.00'),
        surcharge_pct=Decimal('0.00'),
        discount_pct=Decimal('0.00'),
        amount_due=Decimal('50.00'),
        due_date=date.today(),
        state=Installment.State.PENDING,
        paid_amount=None,
        paid_at=None,
        updated_by=user,
    )

    ser = InstallmentSerializer(inst)
    data = ser.data

    assert data['purchase'] == purchase.pk
    assert data['num_installment'] == 1
    assert Decimal(data['base_amount']) == Decimal('50.00')


@pytest.mark.django_db
def test_installment_information_serializer_validation(purchase):
    payload = {
        'purchase_id': purchase.pk,
        'num_installment': 2,
        'base_amount': '25.00',
        'surcharge_pct': '0.00',
        'discount_pct': '0.00',
        'amount_due': '25.00',
        'due_date': date.today().isoformat(),
        'state': 'PENDING',
        'paid_amount': '0.00',
        'paid_at': None,
    }
    ser = InstallmentInformationSerializer(data=payload)
    assert ser.is_valid(), ser.errors
    out = ser.validated_data
    assert out['purchase_id'].pk == purchase.pk
    assert out['num_installment'] == 2


@pytest.mark.django_db
def test_payment_serializer_happy_and_unique_external_ref(purchase, user):
    # create installment
    inst = Installment.objects.create(
        purchase=purchase,
        num_installment=1,
        base_amount=Decimal('50.00'),
        surcharge_pct=Decimal('0.00'),
        discount_pct=Decimal('0.00'),
        amount_due=Decimal('50.00'),
        due_date=date.today(),
        state=Installment.State.PENDING,
        paid_amount=None,
        paid_at=None,
        updated_by=user,
    )

    payload = {
        'installment': inst.pk,
        'amount': '50.00',
        'payment_method': Payment.Method.CARD,
        'external_ref': 'ABC123'
    }
    ser = PaymentSerializer(data=payload)
    assert ser.is_valid(), ser.errors
    p = ser.save()
    assert p.external_ref == 'ABC123'

    # Attempt to create another payment with same external_ref -> should raise IntegrityError on save
    ser2 = PaymentSerializer(data={**payload})
    # DRF ModelSerializer will validate model-level unique constraints and
    # reject the payload before save. Expect a validation error on external_ref.
    assert not ser2.is_valid()
    assert 'external_ref' in ser2.errors
