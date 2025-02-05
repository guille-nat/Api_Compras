
from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
schema_view = get_schema_view(
    openapi.Info(
        title="Sistema de Compras API",
        default_version='v1',
        description="API diseñada para la gestión de compras, pagos, cuotas, inventario y usuarios.\n Este proyecto incluye validaciones robustas y reglas de negocio para asegurar un manejo eficiente y seguro de las operaciones.",
        terms_of_service="https://www.nataliullacoder.com",
        contact=openapi.Contact(email="guillermonatali22@gmail.com"),
        license=openapi.License(name="BSD License nataliullacoder.com"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    path('api/', include("api.urls")),
    path('doc', schema_view.with_ui('swagger',
         cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc',
         cache_timeout=0), name='schema-redoc'),

]
