from rest_framework import serializers
from api.products.models import Product
from api.storage_location.models import StorageLocation
from .models import InventoryRecord


class PurchaseEntryInSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all())
    to_location = serializers.PrimaryKeyRelatedField(
        queryset=StorageLocation.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    batch_code = serializers.CharField(
        required=False, allow_null=True, allow_blank=True)
    expiry_date = serializers.DateField(required=False, allow_null=True)
    description = serializers.CharField(
        required=False, allow_blank=True, default="")
    reference_id = serializers.IntegerField()


class ExitSaleInSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all())
    from_location = serializers.PrimaryKeyRelatedField(
        queryset=StorageLocation.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    description = serializers.CharField(
        required=False, allow_blank=True, default="")
    reference_id = serializers.IntegerField()


class TransferInSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all())
    from_location = serializers.PrimaryKeyRelatedField(
        queryset=StorageLocation.objects.all())
    to_location = serializers.PrimaryKeyRelatedField(
        queryset=StorageLocation.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    description = serializers.CharField(
        required=False, allow_blank=True, default="")
    reference_id = serializers.IntegerField()


class AdjustmentInSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all())
    from_location = serializers.PrimaryKeyRelatedField(
        queryset=StorageLocation.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    description = serializers.CharField(
        required=False, allow_blank=True, default="")
    reference_id = serializers.IntegerField()
    batch_code = serializers.CharField(
        required=False, allow_null=True, allow_blank=True)
    expiry_date = serializers.DateField(required=False, allow_null=True)

    # banderas
    aggregate = serializers.BooleanField(required=False, default=False)
    remove = serializers.BooleanField(required=False, default=False)
    adjusted_other = serializers.BooleanField(required=False, default=False)

    # posibles modificaciones
    modify_expiry_date = serializers.DateField(required=False, allow_null=True)
    modify_batch_code = serializers.CharField(
        required=False, allow_null=True, allow_blank=True)
    modify_location = serializers.PrimaryKeyRelatedField(
        queryset=StorageLocation.objects.all(), required=False, allow_null=True
    )


class ReturnEntryInSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all())
    to_location = serializers.PrimaryKeyRelatedField(
        queryset=StorageLocation.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    description = serializers.CharField(
        required=False, allow_blank=True, default="")
    reference_id = serializers.IntegerField()
    batch_code = serializers.CharField(
        required=False, allow_null=True, allow_blank=True)
    expiry_date = serializers.DateField(required=False, allow_null=True)


class ReturnOutputInSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all())
    from_location = serializers.PrimaryKeyRelatedField(
        queryset=StorageLocation.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    description = serializers.CharField(
        required=False, allow_blank=True, default="")
    reference_id = serializers.IntegerField()
    batch_code = serializers.CharField(
        required=False, allow_null=True, allow_blank=True)
    expiry_date = serializers.DateField(required=False, allow_null=True)


# Para responder con IR (opcional)
class InventoryRecordOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryRecord
        fields = ["id", "product", "location", "quantity",
                  "batch_code", "expiry_date", "updated_at"]
