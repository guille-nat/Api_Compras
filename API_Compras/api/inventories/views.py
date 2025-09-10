from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import UserRateThrottle
from . import services
from .serializers import (
    PurchaseEntryInSerializer, ExitSaleInSerializer, TransferInSerializer,
    AdjustmentInSerializer, ReturnEntryInSerializer, ReturnOutputInSerializer,
    InventoryRecordOutSerializer,
)
from rest_framework.permissions import IsAdminUser
import logging

logger = logging.getLogger(__name__)


class PurchaseEntryView(CreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = PurchaseEntryInSerializer
    throttle_classes = [UserRateThrottle]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            result = services.purchase_entry_inventory(
                product=serializer.validated_data["product"],
                to_location=serializer.validated_data["to_location"],
                quantity=serializer.validated_data["quantity"],
                batch_code=serializer.validated_data.get("batch_code"),
                expiry_date=serializer.validated_data.get("expiry_date"),
                description=serializer.validated_data.get("description", ""),
                reference_id=serializer.validated_data["reference_id"],
                user=request.user,
            )
            
            logger.info(f"Purchase entry created successfully: {result['message']}")
            return Response({
                "success": True,
                "message": result["message"],
                "data": {
                    "inventory": InventoryRecordOutSerializer(result["data"]["inventory"]).data,
                    "quantity_added": result["data"]["quantity_added"],
                    "location": result["data"]["location"],
                    "product": result["data"]["product"]
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating purchase entry: {str(e)}")
            return Response({
                "success": False,
                "message": "Error al registrar entrada de compra",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class ExitSaleView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        try:
            serializer = ExitSaleInSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            result = services.exit_sale_inventory(
                product=serializer.validated_data["product"],
                from_location=serializer.validated_data["from_location"],
                quantity=serializer.validated_data["quantity"],
                description=serializer.validated_data.get("description", ""),
                reference_id=serializer.validated_data.get("reference_id", None),
                user=request.user
            )
            
            logger.info(f"Exit sale processed successfully: {result['message']}")
            return Response(result, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error processing exit sale: {str(e)}")
            return Response({
                "success": False,
                "message": "Error al procesar salida por venta",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class TransferInView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        try:
            serializer = TransferInSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            result = services.transference_inventory(
                product=serializer.validated_data["product"],
                from_location=serializer.validated_data["from_location"],
                to_location=serializer.validated_data["to_location"],
                description=serializer.validated_data.get("description", ""),
                quantity=serializer.validated_data["quantity"],
                reference_id=serializer.validated_data.get("reference_id", None),
                user=request.user  # Fixed: was request.data, should be request.user
            )
            
            logger.info(f"Transfer processed successfully: {result['message']}")
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error processing transfer: {str(e)}")
            return Response({
                "success": False,
                "message": "Error al procesar transferencia",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class AdjustmentInView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        try:
            serializer = AdjustmentInSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            result = services.adjustment_inventory(
                product=serializer.validated_data["product"],
                from_location=serializer.validated_data["from_location"],
                quantity=serializer.validated_data["quantity"],
                description=serializer.validated_data.get("description", ""),
                reference_id=serializer.validated_data.get("reference_id", None),
                batch_code=serializer.validated_data.get("batch_code", None),
                expiry_date=serializer.validated_data.get("expiry_date", None),
                aggregate=serializer.validated_data.get("aggregate", False),
                remove=serializer.validated_data.get("remove", False),
                adjusted_other=serializer.validated_data.get(
                    "adjusted_other", False),
                modify_batch_code=serializer.validated_data.get(
                    "modify_batch_code", None),
                modify_expiry_date=serializer.validated_data.get(
                    "modify_expiry_date", None),
                modify_location=serializer.validated_data.get(
                    "modify_location", None),
                user=request.user
            )
            
            logger.info(f"Adjustment processed successfully: {result['message']}")
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error processing adjustment: {str(e)}")
            return Response({
                "success": False,
                "message": "Error al procesar ajuste de inventario",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class ReturnEntryView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        try:
            serializer = ReturnEntryInSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            result = services.return_entry_inventory(
                product=serializer.validated_data["product"],
                to_location=serializer.validated_data["to_location"],
                quantity=serializer.validated_data["quantity"],
                description=serializer.validated_data.get("description", ""),
                reference_id=serializer.validated_data.get("reference_id", None),
                batch_code=serializer.validated_data.get("batch_code", None),
                expiry_date=serializer.validated_data.get("expiry_date", None),
                user=request.user  # Fixed: was request.data, should be request.user
            )
            
            logger.info(f"Return entry processed successfully: {result['message']}")
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error processing return entry: {str(e)}")
            return Response({
                "success": False,
                "message": "Error al procesar entrada por devolución",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class ReturnOutputView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        try:
            serializer = ReturnOutputInSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            result = services.return_output_inventory(
                product=serializer.validated_data["product"],
                from_location=serializer.validated_data["from_location"],
                quantity=serializer.validated_data["quantity"],
                description=serializer.validated_data.get("description", ""),
                reference_id=serializer.validated_data.get("reference_id", None),
                batch_code=serializer.validated_data.get("batch_code", None),
                expiry_date=serializer.validated_data.get("expiry_date", None),
                user=request.user  # Fixed: was request.data, should be request.user
            )
            
            logger.info(f"Return output processed successfully: {result['message']}")
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error processing return output: {str(e)}")
            return Response({
                "success": False,
                "message": "Error al procesar salida por devolución",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
