from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from api.users.view import UserViewSet
from api.payments.views import PaymentInstallmentViewSet
from api.products.views import ProductViewSet
from api.purchases.views import PurchaseViewSet
from api.categories.view import CategoryPublicViewSet, CategorySerializer
from rest_framework import routers


router = routers.DefaultRouter(trailing_slash=False)  # Elimina la barra final
router.register(r'users', UserViewSet, basename='users')
router.register(r'products', ProductViewSet, basename='productos')
router.register(r'purchases', PurchaseViewSet, basename='purchases')
router.register(r'payments', PaymentInstallmentViewSet, basename='payments')
router.register(r'categories', CategorySerializer, basename='categories')

urlpatterns = [
    path('token', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls))
]
