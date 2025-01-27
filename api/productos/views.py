from rest_framework.permissions import AllowAny
from api.permissions import IsAdminUser
from .models import Productos
from .serializers import ProductsSerializer
from rest_framework import viewsets


class ProductosViewSet(viewsets.ModelViewSet):
    queryset = Productos.objects.all()
    serializer_class = ProductsSerializer

    def get_permissions(self):
        # Permitir acceso sin autenticación para las acciones 'list' y 'retrieve'
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        # Requerir autenticación para cualquier otra acción
        return [IsAdminUser()]
