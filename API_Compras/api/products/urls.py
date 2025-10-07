
from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
     path('products/', views.get_products, name='get_products'),
     # Accept no-trailing-slash variant because tests call '/api/v2/products' (no slash)
     path('products', views.get_products, name='get_products_no_slash'),
     path('admin/products/create/', views.create_product, name='create_product'),
     # Accept no-trailing-slash for create (tests call '/api/v2/admin/products/create')
     path('admin/products/create', views.create_product, name='create_product_no_slash'),
    path('admin/products/<int:product_id>/update/',
         views.update, name='update_product'),
    path('admin/products/bulk-create/',
         views.bulk_create, name='bulk_create_products'),
]
