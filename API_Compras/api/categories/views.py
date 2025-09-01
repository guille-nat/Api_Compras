from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from .serializer import CategoryPrivateSerializer, CategoryPublicSerializer
from . import services, selectors
from rest_framework.throttling import UserRateThrottle


class CategoryPrivateViewSet(ModelViewSet):
    queryset = selectors.list_categories_admin()
    serializer_class = CategoryPrivateSerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def perform_create(self, serializer):
        category = services.create_category(
            user=self.request.user, name=serializer.validated_data["name"])
        # reasigna la instancia de la categoría
        serializer.instance = category

    def perform_update(self, serializer):
        category = self.get_object()

        # Solo se aplica si se puede renombrar.
        if "name" in serializer.validated_data:
            services.rename_category(
                user=self.request.user, category=category, new_name=serializer.validated_data["name"])
            serializer.instance.refresh_from_db()


class CategoryPublicViewSet(ReadOnlyModelViewSet):
    queryset = selectors.list_categories_public()
    throttle_classes = [UserRateThrottle]
    serializer_class = CategoryPublicSerializer
    permission_classes = [AllowAny]
