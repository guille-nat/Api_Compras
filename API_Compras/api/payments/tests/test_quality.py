import pytest


@pytest.mark.django_db
def test_pay_view_missing_field_returns_400():
    from rest_framework.test import APIRequestFactory, force_authenticate
    from django.contrib.auth import get_user_model
    from api.purchases.models import Purchase
    from api.payments.models import Installment
    from api.payments import views
    from django.utils import timezone

    User = get_user_model()
    user = User.objects.create_user(
        username='miss', password='pw', email='miss@example.test')
    purchase = Purchase.objects.create(user=user, purchase_date=timezone.now())
    inst = Installment.objects.create(
        purchase=purchase, num_installment=1, base_amount='5.00', amount_due='5.00')

    factory = APIRequestFactory()
    # omit payment_method
    req = factory.post(
        '/api/payments/pay', {'installment_id': inst.id, 'paid_amount': '5.00'}, format='json')
    force_authenticate(req, user=user)
    resp = views.pay(req)
    resp.render()
    assert resp.status_code == 400
    assert resp.data['success'] is False
    assert 'Campo requerido faltante' in resp.data['message']


@pytest.mark.django_db
def test_pay_view_service_validationerror_returns_400(monkeypatch):
    from rest_framework.test import APIRequestFactory, force_authenticate
    from django.contrib.auth import get_user_model
    from api.purchases.models import Purchase
    from api.payments.models import Installment
    from api.payments import views
    from django.utils import timezone
    from django.core.exceptions import ValidationError

    User = get_user_model()
    user = User.objects.create_user(
        username='valerr', password='pw', email='valerr@example.test')
    purchase = Purchase.objects.create(user=user, purchase_date=timezone.now())
    inst = Installment.objects.create(
        purchase=purchase, num_installment=1, base_amount='7.00', amount_due='7.00')

    def fake_raise(*args, **kwargs):
        raise ValidationError('invalid payment')

    monkeypatch.setattr('api.payments.views.pay_installment', fake_raise)

    factory = APIRequestFactory()
    req = factory.post('/api/payments/pay', {'installment_id': inst.id,
                       'paid_amount': '7.00', 'payment_method': 'CASH'}, format='json')
    force_authenticate(req, user=user)
    resp = views.pay(req)
    resp.render()
    assert resp.status_code == 400
    assert resp.data['success'] is False
    assert 'Error de validación' in resp.data['message']


@pytest.mark.django_db
def test_pay_view_invalid_paid_amount_returns_500():
    # Current behavior: invalid decimal in paid_amount results in server error
    from rest_framework.test import APIRequestFactory, force_authenticate
    from django.contrib.auth import get_user_model
    from api.purchases.models import Purchase
    from api.payments.models import Installment
    from api.payments import views
    from django.utils import timezone

    User = get_user_model()
    user = User.objects.create_user(
        username='invamt', password='pw', email='invamt@example.test')
    purchase = Purchase.objects.create(user=user, purchase_date=timezone.now())
    inst = Installment.objects.create(
        purchase=purchase, num_installment=1, base_amount='9.00', amount_due='9.00')

    factory = APIRequestFactory()
    # send non-decimal string
    req = factory.post('/api/payments/pay', {'installment_id': inst.id,
                       'paid_amount': 'not-a-number', 'payment_method': 'CASH'}, format='json')
    force_authenticate(req, user=user)
    resp = views.pay(req)
    resp.render()
    # The current view does not explicitly catch InvalidOperation; it bubbles to 500
    assert resp.status_code == 500
    assert resp.data['success'] is False


@pytest.mark.django_db
def test_get_all_payments_by_user_nonexistent_raises_404():
    from api.payments.utils import get_all_payments_by_user
    from django.http import Http404

    with pytest.raises(Http404):
        get_all_payments_by_user(99999999)


@pytest.mark.django_db
def test_installment_information_serializer_invalid_payload():
    from api.payments.serializers import InstallmentInformationSerializer
    from datetime import date

    payload = {
        'purchase_id': 'not-a-pk',  # invalid type
        'num_installment': -1,      # invalid negative
        'base_amount': '-25.00',    # negative amount
        'surcharge_pct': '0.00',
        'discount_pct': '0.00',
        'amount_due': '-25.00',
        'due_date': date.today().isoformat(),
        'state': 'PENDING',
        'paid_amount': '0.00',
        'paid_at': None,
    }

    ser = InstallmentInformationSerializer(data=payload)
    assert not ser.is_valid()
    # Expect errors for purchase_id and num_installment / amounts
    assert 'purchase_id' in ser.errors or 'num_installment' in ser.errors
