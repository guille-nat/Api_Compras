import pytest


@pytest.mark.django_db
def test_pay_view_success(monkeypatch):
    from rest_framework.test import APIRequestFactory, force_authenticate
    from django.contrib.auth import get_user_model
    from api.payments import views
    from api.purchases.models import Purchase
    from api.payments.models import Installment, Payment
    from django.utils import timezone
    from decimal import Decimal

    User = get_user_model()
    user = User.objects.create_user(
        username='payvuser', password='pw', email='pv@example.test')
    purchase = Purchase.objects.create(user=user, purchase_date=timezone.now())
    inst = Installment.objects.create(
        purchase=purchase, num_installment=1, base_amount='10.00', amount_due='10.00')

    factory = APIRequestFactory()

    def fake_pay_installment(installment_id, paid_amount, payment_method, external_reference=None):
        # create a Payment record to be serialized
        payment = Payment.objects.create(
            installment=inst, amount=paid_amount, payment_method=payment_method)
        return {
            'success': True,
            'message': 'Pago procesado',
            'data': {
                'installment': inst,
                'payment': payment,
                'amount_paid': str(paid_amount),
                'discount_applied': False
            }
        }

    monkeypatch.setattr(
        'api.payments.views.pay_installment', fake_pay_installment)

    req = factory.post('/api/payments/pay', {'installment_id': inst.id,
                       'paid_amount': '10.00', 'payment_method': 'CASH'}, format='json')
    force_authenticate(req, user=user)
    resp = views.pay(req)
    resp.render()
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert 'payment' in resp.data['data']


@pytest.mark.django_db
def test_get_all_payments_view(monkeypatch):
    from rest_framework.test import APIRequestFactory, force_authenticate
    from django.contrib.auth import get_user_model
    from api.payments import views
    from api.purchases.models import Purchase
    from api.payments.models import Installment, Payment
    from django.utils import timezone

    User = get_user_model()
    user = User.objects.create_user(
        username='paylist', password='pw', email='plist@example.test')
    purchase = Purchase.objects.create(user=user, purchase_date=timezone.now())
    inst = Installment.objects.create(
        purchase=purchase, num_installment=1, base_amount='15.00', amount_due='15.00')
    payment = Payment.objects.create(
        installment=inst, amount='15.00', payment_method='CARD')

    # monkeypatch the util used by the view to return our payment
    monkeypatch.setattr(
        'api.payments.views.get_all_payments_by_user', lambda uid: [payment])

    factory = APIRequestFactory()
    req = factory.get('/api/payments/all')
    force_authenticate(req, user=user)
    resp = views.get_all_payments(req)
    resp.render()
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert resp.data['data']['total_count'] == 1
