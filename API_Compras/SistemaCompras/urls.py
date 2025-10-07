from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from .views import home
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

# Custom views without throttling for documentation


class NoThrottleSpectacularAPIView(SpectacularAPIView):
    throttle_classes = []


class NoThrottleSpectacularSwaggerView(SpectacularSwaggerView):
    throttle_classes = []


class NoThrottleSpectacularRedocView(SpectacularRedocView):
    throttle_classes = []


# Configuración para drf-yasg (respaldo)
schema_view = get_schema_view(
    openapi.Info(
        title="🛒 API Sistema de Compras",
        default_version='v2.0.0',
        description="""
        ## 📄 Descripción
        API diseñada para la gestión completa de compras, pagos, cuotas, inventario y usuarios.
        
        ## 🔒 Autenticación
        Esta API utiliza JWT (JSON Web Tokens) con esquema Bearer.
        
        **Ejemplo de uso:**
        ```
        Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
        ```
        """,
        terms_of_service="https://www.nataliullacoder.com/terms/",
        contact=openapi.Contact(
            name="Guillermo Natali Ulla",
            email="guillermonatali22@gmail.com",
            url="https://nataliullacoder.com/"
        ),
        license=openapi.License(
            name="MIT License",
            url="https://opensource.org/licenses/MIT"
        ),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),

    # === API Routes ===#
    path('api/v2/', include("api.urls")),

    # === Documentación con drf-spectacular (Recomendado) ===#
    path('api/v2/schema/', NoThrottleSpectacularAPIView.as_view(), name='schema'),
    path('api/v2/schema/swagger-ui/',
         NoThrottleSpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v2/schema/redoc/',
         NoThrottleSpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # === Home ===#
    path('', home, name='home'),
]
