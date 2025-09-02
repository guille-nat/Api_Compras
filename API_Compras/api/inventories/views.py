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


class PurchaseEntryView(CreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = PurchaseEntryInSerializer
    throttle_classes = [UserRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ir = services.purchase_entry_inventory(
            product=serializer.validated_data["product"],
            to_location=serializer.validated_data["to_location"],
            quantity=serializer.validated_data["quantity"],
            batch_code=serializer.validated_data.get("batch_code"),
            expiry_date=serializer.validated_data.get("expiry_date"),
            description=serializer.validated_data.get("description", ""),
            reference_id=serializer.validated_data["reference_id"],
            user=request.user,
        )
        return Response(InventoryRecordOutSerializer(ir).data, status=status.HTTP_201_CREATED)


class ExitSaleView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
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
        return Response(result, status=status.HTTP_201_CREATED)


class TransferInView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        serializer = TransferInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.transference_inventory(
            product=serializer.validated_data["product"],
            from_location=serializer.validated_data["from_location"],
            to_location=serializer.validated_data["to_location"],
            description=serializer.validated_data.get("description", ""),
            quantity=serializer.validated_data["quantity"],
            reference_id=serializer.validated_data.get("reference_id", None),
            user=request.data
        )
        return Response(result, status=status.HTTP_200_OK)


class AdjustmentInView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
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
        return Response(result, status=status.HTTP_200_OK)


class ReturnEntryView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
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
            user=request.data
        )
        return Response(result, status=status.HTTP_200_OK)


class ReturnOutputView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
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
            user=request.data
        )
        return Response(result, status=status.HTTP_200_OK)
