from rest_framework.permissions import AllowAny
from api.permissions import IsAdminUser
from .models import Product
from .serializers import ProductSerializer
from rest_framework import viewsets


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_permissions(self):
        # Permitir acceso sin autenticación para las acciones 'list' y 'retrieve'
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        # Requerir autenticación para cualquier otra acción
        return [IsAdminUser()]
