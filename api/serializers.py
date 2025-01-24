from django.contrib.auth.models import User
from rest_framework import serializers
from .models import (
    Products, Compras,
    Cuotas, Pagos, DetallesCompras,
    Notificacion
)
from django.db import transaction
from rest_framework.exceptions import ValidationError
from datetime import timedelta, date


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email',
            'password'
        ]
        read_only_fields = ["id",]
        extra_kwargs = {
            'password': {'write_only': True}
        }

    # def create(self, validated_data):
    #     # Crear el usuario
    #     user = User.objects.create_user(
    #         username=validated_data['username'],
    #         email=validated_data.get('email'),
    #         password=validated_data['password'],
    #         first_name=validated_data.get('first_name', ''),
    #         last_name=validated_data.get('last_name', '')
    #     )

    #     return user


class ProductsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Products
        fields = [
            'id', 'cod_products', 'nombre',
            'marca', 'modelo', 'precio_unitario',
            'stock'
        ]
        read_only_fields = ['id',]


class DetallesComprasSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetallesCompras
        # Campos necesarios para el detalle
        fields = ['products', 'cantidad_productos']


class ComprasSerializer(serializers.ModelSerializer):
    detalles = DetallesComprasSerializer(many=True)  # Relación con el detalle

    class Meta:
        model = Compras
        fields = [
            'id', 'usuario', 'fecha_compra',
            'cuotas_totales', 'descuento_aplicado',
            'detalles'
        ]
        read_only_field = ['id', 'monto_total']

    def validate(self, attrs):
        # Validar que las cuotas sean mayores a 0
        if attrs['cuotas_totales'] <= 0:
            raise serializers.ValidationError(
                {"error": "El número de cuotas debe ser mayor a 0."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles')  # Extraer los detalles
        cuotas_totales = validated_data['cuotas_totales']
        fecha_compra = validated_data['fecha_compra']
        descuento_aplicado = validated_data.get('descuento_aplicado', 0) / 100

        # Pre-carga de los productos implicados
        product_ids = [detalle['products'].id for detalle in detalles_data]
        productos = {producto.id: producto for producto in Products.objects.filter(
            id__in=product_ids).select_for_update()}  # Aplicar bloqueo en la base de datos para evitar concurrencia

        errors = []
        monto_total = 0

        # Validar la existencia de productos y stock
        for detalle in detalles_data:
            producto = productos.get(detalle['products'].id)

            if not producto:
                errors.append(
                    {'error': f'El producto con ID {detalle["products"].id} no existe.'})

            if producto.stock < detalle['cantidad_productos']:
                errors.append(
                    {'error': f"El stock del producto '{producto.nombre}' es insuficiente. Disponible: {producto.stock}, requerido: {detalle['cantidad_productos']}"}
                )
            else:
                monto_total += producto.precio_unitario * \
                    detalle['cantidad_productos']
        if errors:
            raise ValidationError(errors)

        # Aplicar aumento en cuotas mayores a 6
        if cuotas_totales > 6:
            monto_total += monto_total * 0.15  # 15% de aumento

        fecha_vencimiento = fecha_compra + \
            timedelta(days=cuotas_totales * 30)

        if descuento_aplicado > 0:
            monto_total -= monto_total * descuento_aplicado

        compra = Compras.objects.create(
            monto_total=monto_total,
            fecha_vencimiento=fecha_vencimiento,
            cuota_actual=1, ** validated_data)  # Crear la compra

        # Crear los detalles de la compra
        detalles_obj = [
            DetallesCompras(compras=compra, **detalle) for detalle in detalles_data
        ]
        DetallesCompras.objects.bulk_create(detalles_obj)

        # Descontar el stock de cada producto
        for detalle in detalles_data:
            producto = productos[detalle['products'].id]
            producto.stock -= detalle['cantidad_productos']

        # Actualizar el stock de todos los productos
        Products.objects.bulk_update(productos.values(), ['stock'])

        # Crear cuotas
        monto_por_cuota = monto_total / cuotas_totales
        for i in range(cuotas_totales):
            fecha_vencimiento_cuota = fecha_compra + \
                timedelta(days=(i + 1) * 30)
            Cuotas.objects.create(
                compra=compra,
                numero_cuota=i + 1,
                monto=monto_por_cuota,
                fecha_vencimiento=fecha_vencimiento_cuota
            )

        return compra


class CuotasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cuotas
        fields = [
            'id', 'compra', 'nro_cuota', 'monto',
            'fecha_vencimiento', 'estado'
        ]
        read_only_fields = ['id',]


class PagosSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pagos
        fields = [
            'id', 'cuotas', 'fecha_pago', 'monto',
            'medio_pago', 'descuento_aplicado'
        ]
        read_only_fields = ['id',]


class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = [
            'id', 'mensaje', 'fecha_creacion', 'envidada'
        ]
