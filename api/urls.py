from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    UserViewSet,
    ProductsViewSet, CompraViewSet,

)
from rest_framework import routers


router = routers.DefaultRouter()
router.register(r'user', UserViewSet, basename='users')
router.register(r'products', ProductsViewSet, basename='products')
router.register(r'compras', CompraViewSet, basename='compras')

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls))
]
