from rest_framework import serializers
from .models import InventoryRecord

# Para responder con IR (opcional)


class InventoryRecordOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryRecord
        fields = ["id", "product", "location", "quantity",
                  "batch_code", "expiry_date", "updated_at"]


class InventoryRecordWithDetailsSerializer(serializers.Serializer):
    """
    Serializer para registros de inventario con información adicional.
    Maneja el formato de datos devuelto por get_inventory_record().
    """
    # Información básica del registro
    record_id = serializers.IntegerField(source='record.id', read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    batch_code = serializers.CharField(read_only=True)
    expiry_date = serializers.DateField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    # Información del producto
    product_id = serializers.IntegerField(read_only=True)
    product_name = serializers.CharField(read_only=True)

    # Información de la ubicación
    location_id = serializers.IntegerField(read_only=True)
    location_name = serializers.CharField(read_only=True)

    class Meta:
        fields = [
            'record_id', 'quantity', 'batch_code', 'expiry_date',
            'created_at', 'updated_at', 'product_id', 'product_name',
            'location_id', 'location_name'
        ]
