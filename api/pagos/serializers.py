from rest_framework import serializers
from .models import Pagos, Cuotas


class PagosSerializer(serializers.ModelSerializer):
    cuotas = serializers.PrimaryKeyRelatedField(
        queryset=Cuotas.objects.all(),  # Asegura que el ID de la cuota exista
        help_text="ID de la cuota a la que se aplica el pago."
    )

    class Meta:
        model = Pagos
        fields = [
            'id', 'cuotas',
            'medio_pago'
        ]
        read_only_fields = ['id',]
