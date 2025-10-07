"""
Serializers for the payments app.

Follow project docstring style: short module description, then serializer classes for
Installment and Payment objects used by the API and internal services.

See also: api/purchases/models.py (Purchase) used for related fields.
"""

from rest_framework import serializers
from .models import Payment, Installment
from api.purchases.models import Purchase
from api.serializer_mixins import AuditableSerializerMixin


class InstallmentSerializer(AuditableSerializerMixin, serializers.ModelSerializer):
    """
    Serializer for the Installment model con campos de auditoría automáticos.

    Utiliza AuditableSerializerMixin para eliminar redundancia en:
    - fields = '__all__'
    - read_only_fields para campos de auditoría

    Elimina ~5 líneas de código repetitivo de configuración Meta.
    """

    class Meta(AuditableSerializerMixin.Meta):
        model = Installment


class InstallmentInformationSerializer(serializers.Serializer):
    """Lightweight serializer used for exchanging installment information.

    This serializer is not directly tied to the model and is useful for
    API payloads or reports where a subset of installment data is required.
    """

    id = serializers.IntegerField(read_only=True)
    purchase_id = serializers.PrimaryKeyRelatedField(
        queryset=Purchase.objects.all())
    num_installment = serializers.IntegerField()
    base_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    surcharge_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    discount_pct = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True)
    amount_due = serializers.DecimalField(max_digits=10, decimal_places=2)
    due_date = serializers.DateField()
    state = serializers.CharField(max_length=20)
    paid_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    paid_at = serializers.DateTimeField(allow_null=True)


class PaymentSerializer(AuditableSerializerMixin, serializers.ModelSerializer):
    """
    Serializer for Payment model con campos de auditoría automáticos.

    Utiliza AuditableSerializerMixin para eliminar redundancia en:
    - fields = '__all__'
    - read_only_fields para campos de auditoría

    Elimina ~5 líneas de código repetitivo de configuración Meta.
    """

    class Meta(AuditableSerializerMixin.Meta):
        model = Payment
