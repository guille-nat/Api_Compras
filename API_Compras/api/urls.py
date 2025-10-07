from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework import routers
from .views import NotificationTemplateViewSet

router = routers.DefaultRouter(trailing_slash=False)  # Elimina la barra final
# === NotificationTemplate ===#
router.register(r'admin/notification-templates',
                NotificationTemplateViewSet, basename='notification-templates')

urlpatterns = [
    # === Autenticación JWT ===#
    path('token', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh', TokenRefreshView.as_view(), name='token_refresh'),

    # === Users - Function-based views ===#
    path('', include('api.users.urls')),

    # === Router de ViewSets ===#
    path('', include(router.urls)),

    # === Inventories - Function-based views ===#
    path('', include('api.inventories.urls')),

    # === Categories - Function-based views ===#
    path('', include('api.categories.urls', namespace='categories')),

    # === Products - Function-based views ===#
    path('', include('api.products.urls', namespace='products')),

    # === Promotions - Function-based views ===#
    path('promotions/', include('api.promotions.urls', namespace='promotions')),

    # === StorageLocation ===#
    path('admin/storage-locations', include('api.storage_location.urls')),

    # === Payments & Installments ===#
    path('', include('api.payments.urls')),

    # === Purchases - Function-based views ===#
    path('', include('api.purchases.urls')),

    # === Analytics - Reports ===#
    path('admin/analytics/', include('api.analytics.urls')),

    # === Cache Management ===#
    path('admin/cache/', include('api.cache.cache_urls')),
]
