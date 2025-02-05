from rest_framework import serializers
from .models import Payment, Installment


class PaymentSerializer(serializers.ModelSerializer):
    installment = serializers.PrimaryKeyRelatedField(
        queryset=Installment.objects.all(),  # Asegura que el ID de la cuota exista
        help_text="ID de la cuota a la que se aplica el pago."
    )

    class Meta:
        model = Payment
        fields = [
            'id', 'installment',
            'payment_method'
        ]
        read_only_fields = ['id',]
