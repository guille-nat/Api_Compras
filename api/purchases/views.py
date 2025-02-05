from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Purchase
from .serializers import PurchaseSerializer


class PurchaseViewSet(viewsets.ModelViewSet):
    queryset = Purchase.objects.all()
    serializer_class = PurchaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Purchase.objects.all()
        return Purchase.objects.filter(user=self.request.user)
