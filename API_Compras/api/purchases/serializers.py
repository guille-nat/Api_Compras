from rest_framework import serializers
from .models import PurchaseDetail, Purchase
from django.db import transaction
from rest_framework.exceptions import ValidationError
from api.products.models import Product
from api.payments.models import Installment
from decimal import Decimal
from datetime import timedelta


class PurchaseDetailSerializer(serializers.ModelSerializer):
    # External API (and existing tests/docs) use the key `cant_product`.
    # The model field is `quantity`, so map the incoming/outgoing name
    # to the model using `source='quantity'` so we keep backward
    # compatibility without changing tests/clients.
    cant_product = serializers.IntegerField(source='quantity', min_value=1)

    class Meta:
        model = PurchaseDetail
        fields = ['product', 'cant_product']


class PurchaseSerializer(serializers.ModelSerializer):
    details = PurchaseDetailSerializer(many=True)  # Relación con el detalle
    # amount_paid does not exist on the model but is expected by API consumers
    # and by previous serializer configuration; expose it as a read-only field
    amount_paid = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True, default=Decimal('0')
    )

    class Meta:
        model = Purchase
        fields = [
            'id', 'user', 'purchase_date',
            'total_installments_count', 'discount_applied',
            'details', 'total_amount', 'amount_paid'
        ]
        # Make `user` read-only so callers can provide the user at
        # save-time: serializer.save(user=the_user). This keeps the
        # external payload free of the user field while allowing the
        # view/tests to inject it.
        read_only_fields = ['id', 'user', 'total_amount', 'amount_paid']
        extra_kwargs = {
            'total_amount': {'read_only': True},
            'amount_paid': {'read_only': True}
        }

    def validate(self, attrs):
        if attrs['total_installments_count'] <= 0:
            raise serializers.ValidationError(
                {"error": "El número de cuotas debe ser mayor a 0."})
        details = attrs.get('details', [])
        if details:
            product_ids = [d['product'].id for d in details]

            q = Product.objects.filter(id__in=product_ids)
            products_iter = q.select_for_update() if hasattr(q, 'select_for_update') else q
            products = {product.id: product for product in products_iter}

            errors = []
            for detail in details:
                prod = products.get(detail['product'].id)
                if not prod:
                    errors.append(
                        {'error': f'El producto con ID {detail["product"].id} no existe.'})
                    continue
                if prod.stock < detail['quantity']:
                    errors.append(
                        {'error': f"El stock del producto '{prod.name}' es insuficiente. Disponible: {prod.stock}, requerido: {detail['quantity']}"})
            if errors:
                first_msg = errors[0].get('error') if isinstance(
                    errors[0], dict) else str(errors[0])
                raise ValidationError({first_msg: errors})

        return attrs

    @transaction.atomic
    def create(self, validated_data, **kwargs):
        # Accept runtime kwargs (e.g. user=...) passed from
        # serializer.save(user=...). Merge them into validated_data so
        # Purchase.objects.create(...) receives them.
        if kwargs:
            validated_data = {**validated_data, **kwargs}
        details_data = validated_data.pop('details')  # Extraer los detalles
        total_installments_count = validated_data['total_installments_count']
        purchase_date = validated_data['purchase_date']
        discount_applied = Decimal(
            validated_data.get('discount_applied', 0)) / 100
        print(discount_applied)

        product_ids = [detalle['product'].id for detalle in details_data]
        q = Product.objects.filter(id__in=product_ids)
        products_iter = q.select_for_update() if hasattr(q, 'select_for_update') else q
        products = {product.id: product for product in products_iter}

        total_amount = 0
        for detail in details_data:
            product = products.get(detail['product'].id)
            total_amount += product.unit_price * detail['quantity']

        # Aplicar aumento en cuotas mayores a 6
        if total_installments_count >= 12:
            total_amount += total_amount * Decimal('0.45')  # 45% de aumento
        elif total_installments_count >= 6:
            total_amount += total_amount * Decimal('0.15')  # 15% de aumento

        if discount_applied > 0:
            total_amount -= total_amount * discount_applied

        purchase_kwargs = {
            'total_amount': total_amount,
            'purchase_date': purchase_date,
            'total_installments_count': total_installments_count,
            'discount_applied': validated_data.get('discount_applied', 0),
        }
        if 'user' in validated_data:
            purchase_kwargs['user'] = validated_data['user']

        purchase = Purchase.objects.create(**purchase_kwargs)

        object_detail = []
        for detail in details_data:
            prod = products[detail['product'].id]
            qty = detail['quantity']
            unit_price = prod.unit_price
            subtotal = unit_price * qty
            object_detail.append(
                PurchaseDetail(
                    purchase=purchase,
                    product=prod,
                    quantity=qty,
                    unit_price_at_purchase=unit_price,
                    subtotal=subtotal,
                )
            )
        PurchaseDetail.objects.bulk_create(object_detail)

        for detail in details_data:
            product = products[detail['product'].id]
            product.stock -= detail['quantity']

        Product.objects.bulk_update(products.values(), ['stock'])

        # Crear cuotas
        amount_x_installment = total_amount / total_installments_count
        for i in range(total_installments_count):
            due_date_installment = purchase_date + \
                timedelta(days=(i + 1) * 30)
            surcharge_pct = Decimal('0')
            if total_installments_count >= 12:
                surcharge_pct = Decimal('45')
            elif total_installments_count >= 6:
                surcharge_pct = Decimal('15')

            discount_pct = Decimal(validated_data.get('discount_applied', 0))

            due_date_value = due_date_installment
            if hasattr(due_date_installment, 'date'):
                try:
                    due_date_value = due_date_installment.date()
                except Exception:
                    due_date_value = due_date_installment

            Installment.objects.create(
                purchase=purchase,
                num_installment=i + 1,
                base_amount=amount_x_installment,
                surcharge_pct=surcharge_pct,
                discount_pct=discount_pct,
                amount_due=amount_x_installment,
                due_date=due_date_value,
                state=Installment.State.PENDING
            )

        return purchase
