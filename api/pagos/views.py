from rest_framework import viewsets, status
from .serializers import PagosSerializer
from .models import Pagos
from rest_framework.permissions import IsAuthenticated
from datetime import date
from decimal import Decimal
from django.db import transaction
from rest_framework.response import Response


class PagosCuotasViewSet(viewsets.ModelViewSet):
    serializer_class = PagosSerializer
    queryset = Pagos.objects.all()
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
        Crea pago y actualiza la cuota
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                cuota = serializer.validated_data['cuotas']
                compra = cuota.compras

                fecha_pago = date.today()
                descuento_aplicado = Decimal('0')

                # Aplicar descuento por pronto pago
                if fecha_pago < cuota.fecha_vencimiento:
                    descuento_aplicado = Decimal('0.5')  # 5% de descuento
                    cuota.monto -= cuota.monto * descuento_aplicado

                # Actualizar el estado de la cuota y los datos de la compra
                cuota.estado = 'PAGADA'
                compra.cuota_actual += 1
                compra.monto_pagado += cuota.monto

                # Crear el pago
                pago = Pagos.objects.create(
                    cuotas=cuota,
                    medio_pago=serializer.validated_data['medio_pago'],
                    monto=cuota.monto,
                    fecha_pago=fecha_pago
                )

                # Guarda los cambios en cuota y compra
                cuota.save(update_fields=['estado', 'monto'])
                compra.save(update_fields=['cuota_actual', 'monto_pagado'])

            # Serializar y devolver la respuesta
            response_serializer = self.get_serializer(pago)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': f'{e}'}, status=status.HTTP_403_FORBIDDEN)
