from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Compras
from .serializers import ComprasSerializer


class CompraViewSet(viewsets.ModelViewSet):
    queryset = Compras.objects.all()
    serializer_class = ComprasSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Compras.objects.all()
        return Compras.objects.filter(usuario=self.request.user)
