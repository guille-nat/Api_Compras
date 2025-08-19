from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Purchase
from .serializers import PurchaseSerializer


class PurchaseViewSet(ModelViewSet):
    serializer_class = PurchaseSerializer

    queryset = Purchase.objects.none()

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        # Cuando drf_yasg arma el esquema, no hay usuario real
        if getattr(self, "swagger_fake_view", False):
            return Purchase.objects.none()

        user = self.request.user
        if not user.is_authenticated:
            return Purchase.objects.none()

        if user.is_superuser:
            return Purchase.objects.all()

        return Purchase.objects.filter(user=user)

    def perform_create(self, serializer):
        # Si tu modelo tiene FK user, asegúrate de setearlo al crear
        serializer.save(user=self.request.user)
