
from rest_framework import serializers
from .models import (PromotionRule, Promotion, PromotionScopeCategory,
                     PromotionScopeLocation, PromotionScopeProduct)
from api.products.serializers import ProductBasicSerializer
from api.categories.serializers import CategoryPublicSerializer
from django.utils import timezone


class PromotionRuleSerializer(serializers.ModelSerializer):
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = PromotionRule
        fields = ['id', 'type', 'value', 'priority',
                  'start_at', 'end_at', 'acumulable', 'is_active']

    def get_is_active(self, obj):
        now = timezone.now()
        return obj.start_at <= now <= obj.end_at


# Serializador conjunto para las relaciones de alcance de la promoción
class PromotionWithAllRelationsSerializer(serializers.ModelSerializer):
    # Incluye reglas (Relación 1:N)
    rules = PromotionRuleSerializer(many=True,
                                    source='promotionrule'  # Relación inversa Django
                                    , read_only=True)

    # Incluye categorías
    categories = serializers.SerializerMethodField()

    # Incluye productos
    products = serializers.SerializerMethodField()

    # Incluye ubicaciones
    locations = serializers.SerializerMethodField()

    # Campo calculado para verificar si la promoción está activa
    has_active_rules = serializers.SerializerMethodField()

    class Meta:
        model = Promotion
        fields = [
            'id', 'name', 'active',
            'rules', 'categories', 'products', 'locations',
            'has_active_rules', 'created_at'
        ]
        read_only_fields = ['id',]

    def get_categories(self, obj):
        categories = []
        for scope in obj.promotionscopecategory.all():
            categories.append(CategoryPublicSerializer(scope.category).data)
        return categories

    def get_products(self, obj):
        products = []
        for scope in obj.promotionscopeproduct.all():
            products.append(ProductBasicSerializer(scope.product).data)
        return products

    def get_locations(self, obj):
        locations = []
        for scope in obj.promotionscopelocation.all():
            locations.append({
                'id': scope.location.id,
                'name': scope.location.name
            })
        return locations

    def get_has_active_rules(self, obj):
        now = timezone.now()
        return obj.promotionrule.filter(
            start_at__lte=now,
            end_at__gte=now
        ).exists()


class PromotionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = ['id', 'name', 'active', 'created_at']
        read_only_fields = ['id', 'created_at']
