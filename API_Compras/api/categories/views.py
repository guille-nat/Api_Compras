from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.response import Response
from rest_framework import status
from .serializer import CategoryPrivateSerializer, CategoryPublicSerializer
from . import services, selectors
from rest_framework.throttling import UserRateThrottle
import logging

logger = logging.getLogger(__name__)


class CategoryPrivateViewSet(ModelViewSet):
    queryset = selectors.list_categories_admin()
    serializer_class = CategoryPrivateSerializer
    permission_classes = [IsAdminUser]
    throttle_classes = [UserRateThrottle]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            result = services.create_category(
                user=request.user, 
                name=serializer.validated_data["name"]
            )
            
            logger.info(f"Category created successfully: {result['message']}")
            
            # Serializar la categoría creada para la respuesta
            category_data = CategoryPrivateSerializer(result["data"]["category"]).data
            
            return Response({
                "success": True,
                "message": result["message"],
                "data": {
                    "category": category_data,
                    "name": result["data"]["name"]
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating category: {str(e)}")
            return Response({
                "success": False,
                "message": "Error al crear categoría",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            
            # Solo se aplica si se puede renombrar
            if "name" in serializer.validated_data:
                result = services.rename_category(
                    user=request.user, 
                    category=instance, 
                    new_name=serializer.validated_data["name"]
                )
                
                logger.info(f"Category updated successfully: {result['message']}")
                
                # Serializar la categoría actualizada para la respuesta
                category_data = CategoryPrivateSerializer(result["data"]["category"]).data
                
                return Response({
                    "success": True,
                    "message": result["message"],
                    "data": {
                        "category": category_data,
                        "old_name": result["data"]["old_name"],
                        "new_name": result["data"]["new_name"]
                    }
                }, status=status.HTTP_200_OK)
            else:
                # Si no hay cambio de nombre, usar el comportamiento estándar
                self.perform_update(serializer)
                return Response({
                    "success": True,
                    "message": "Categoría actualizada exitosamente",
                    "data": {
                        "category": serializer.data
                    }
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Error updating category: {str(e)}")
            return Response({
                "success": False,
                "message": "Error al actualizar categoría",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def perform_update(self, serializer):
        serializer.save()


class CategoryPublicViewSet(ReadOnlyModelViewSet):
    queryset = selectors.list_categories_public()
    throttle_classes = [UserRateThrottle]
    serializer_class = CategoryPublicSerializer
    permission_classes = [AllowAny]
