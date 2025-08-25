from rest_framework import serializers
from .models import PurchaseDetail, Purchase
from django.db import transaction
from rest_framework.exceptions import ValidationError
from api.products.models import Product
from api.payments.models import Installment
from decimal import Decimal
from datetime import timedelta


class PurchaseDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseDetail
        # Campos necesarios para el detalle
        fields = ['product', 'cant_product']


class PurchaseSerializer(serializers.ModelSerializer):
    details = PurchaseDetailSerializer(many=True)  # Relación con el detalle

    class Meta:
        model = Purchase
        fields = [
            'id', 'user', 'purchase_date',
            'total_installments_count', 'discount_applied',
            'details', 'total_amount', 'amount_paid'
        ]
        read_only_field = ['id', 'total_amount', 'amount_paid']
        extra_kwargs = {
            'total_amount': {'read_only': True},
            'amount_paid': {'read_only': True}
        }

    def validate(self, attrs):
        # Validar que las cuotas sean mayores a 0
        if attrs['total_installments_count'] <= 0:
            raise serializers.ValidationError(
                {"error": "El número de cuotas debe ser mayor a 0."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        details_data = validated_data.pop('details')  # Extraer los detalles
        total_installments_count = validated_data['total_installments_count']
        purchase_date = validated_data['purchase_date']
        discount_applied = Decimal(
            validated_data.get('discount_applied', 0)) / 100
        print(discount_applied)

        # Pre-carga de los productos implicados
        product_ids = [detalle['product'].id for detalle in details_data]
        products = {product.id: product for product in Product.objects.filter(
            id__in=product_ids).select_for_update()}  # Aplicar bloqueo en la base de datos para evitar concurrencia

        errors = []
        total_amount = 0

        # Validar la existencia de productos y stock
        for detail in details_data:
            product = products.get(detail['product'].id)

            if not product:
                errors.append(
                    {'error': f'El producto con ID {detail["product"].id} no existe.'})

            if product.stock < detail['cant_product']:
                errors.append(
                    {'error': f"El stock del producto '{product.name}' es insuficiente. Disponible: {product.stock}, requerido: {detail['cant_product']}"}
                )
            else:
                total_amount += product.unit_price * \
                    detail['cant_product']
        if errors:
            raise ValidationError(errors)

        # Aplicar aumento en cuotas mayores a 6
        if total_installments_count >= 12:
            total_amount += total_amount * Decimal('0.45')  # 45% de aumento
        elif total_installments_count >= 6:
            total_amount += total_amount * Decimal('0.15')  # 15% de aumento

        due_date = purchase_date + \
            timedelta(days=total_installments_count * 30)

        if discount_applied > 0:
            total_amount -= total_amount * discount_applied

        purchase = Purchase.objects.create(
            total_amount=total_amount,
            due_date=due_date,
            current_installment=1, ** validated_data)  # Crear la compra

        # Crear los detalles de la compra
        object_detail = [
            PurchaseDetail(purchase=purchase, **detail) for detail in details_data
        ]
        PurchaseDetail.objects.bulk_create(object_detail)

        # Descontar el stock de cada producto
        for detail in details_data:
            product = products[detail['product'].id]
            product.stock -= detail['cant_product']

        # Actualizar el stock de todos los productos
        Product.objects.bulk_update(products.values(), ['stock'])

        # Crear cuotas
        amount_x_installment = total_amount / total_installments_count
        for i in range(total_installments_count):
            due_date_installment = purchase_date + \
                timedelta(days=(i + 1) * 30)
            Installment.objects.create(
                purchase=purchase,
                num_installment=i + 1,
                amount=amount_x_installment,
                due_date_installment=due_date_installment,
                state='PENDIENTE'
            )

        return purchase
