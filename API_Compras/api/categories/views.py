from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from .serializer import CategoryPrivateSerializer, CategoryPublicSerializer
from . import services, selectors


class CategoryPrivateViewSet(ModelViewSet):
    serializer_class = CategoryPrivateSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return selectors.list_categories_admin()

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
    serializer_class = CategoryPublicSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return selectors.list_categories_public()
