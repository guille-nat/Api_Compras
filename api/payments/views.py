from rest_framework import viewsets, status
from .serializers import PaymentSerializer
from .models import Payment
from rest_framework.permissions import IsAuthenticated
from datetime import date
from decimal import Decimal
from django.db import transaction
from rest_framework.response import Response


class PaymentInstallmentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    queryset = Payment.objects.all()
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
        Crea pago y actualiza la cuota
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                installment = serializer.validated_data['installment']
                purchase = installment.purchase

                payment_date = date.today()
                discount_applied = Decimal('0')

                # Aplicar descuento por pronto pago
                if payment_date < installment.due_date_installment:
                    discount_applied = Decimal('0.5')  # 5% de descuento
                    installment.amount -= installment.amount * discount_applied

                # Actualizar el estado de la cuota y los datos de la compra
                installment.state = 'PAGADA'
                purchase.current_installment += 1
                purchase.amount_paid += installment.amount
                payment_method = serializer.validated_data['payment_method'].upper(
                )
                # Crear el pago
                payment = Payment.objects.create(
                    installment=installment,
                    payment_method=payment_method,
                    amount=installment.amount,
                    payment_date=payment_date
                )

                # Guarda los cambios en cuota y compra
                installment.save(update_fields=['state', 'amount'])
                purchase.save(
                    update_fields=['current_installment', 'amount_paid'])

            # Serializar y devolver la respuesta
            response_serializer = self.get_serializer(payment)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': f'{e}'}, status=status.HTTP_403_FORBIDDEN)
