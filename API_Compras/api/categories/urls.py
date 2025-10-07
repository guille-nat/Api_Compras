from django.urls import path
from . import views

app_name = 'categories'

urlpatterns = [
    # === Endpoints de administración (Solo administradores - IsAdminUser) ===#
    path('admin/categories/', views.list_categories_admin,
         name='list-admin'),
    # Also accept no-trailing-slash for tests that request '/api/v2/admin/categories'
    path('admin/categories', views.list_categories_admin,
         name='list-admin-no-slash'),
    path('admin/categories/<int:pk>/',
         views.get_category_admin, name='get-admin'),
    path('admin/categories/create/', views.create_category, name='create'),
     path('admin/categories/create', views.create_category, name='create_no_slash'),
    path('admin/categories/update/<int:pk>/',
         views.update_category, name='update'),
    path('admin/categories/delete/<int:pk>/',
         views.delete_category, name='delete'),

    # === Endpoints públicos (Acceso libre - AllowAny) ===#
    path('categories/', views.list_categories_public,
         name='list_categories_public'),
    path('categories/<int:id>/', views.get_category_public,
         name='get_category_public'),
    path('categories/promotions/', views.get_categories_with_promotions,
         name='get_categories_with_promotions'),
]
