# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Rutas básicas de consulta
    path('purchases', views.purchase_list_create, name='purchase_list_create'),
    path('purchases/<int:purchase_id>',
         views.purchase_detail, name='purchase_detail'),
    path('purchases/my-purchases', views.get_my_purchases, name='get_my_purchases'),

    # Rutas de actualización especializada
    path('purchases/<int:purchase_id>/status',
         views.update_purchase_status, name='update_purchase_status'),
    path('purchases/<int:purchase_id>/installments',
         views.update_purchase_installments, name='update_purchase_installments'),
    path('purchases/<int:purchase_id>/discount',
         views.update_purchase_discount, name='update_purchase_discount'),

    # Rutas administrativas
    path('admin/purchases/all', views.get_admin_all_purchases,
         name='admin_all_purchases'),
    path('admin/purchases/<int:purchase_id>/delete',
         views.admin_delete_purchase, name='admin_delete_purchase'),
]
