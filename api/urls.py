from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from api.usuarios.view import UserViewSet
from api.pagos.views import PagosCuotasViewSet
from api.productos.views import ProductosViewSet
from api.compras.views import CompraViewSet
from rest_framework import routers


router = routers.DefaultRouter()
router.register(r'user', UserViewSet, basename='usuarios')
router.register(r'productos', ProductosViewSet, basename='productos')
router.register(r'compra', CompraViewSet, basename='compras')
router.register(r'pago', PagosCuotasViewSet, basename='pagos')

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls))
]
