from django.urls import path
from .views import (
    list_active_promotions,
    list_promotions_active_products,
    list_categories_with_active_promotions,
    create_promotion,
    create_rule,
    create_promotion_product,
    create_promotion_category,
    create_promotion_location,
    update_promotion,
    update_rule,
    delete_promotion,
    delete_rule,
    delete_promotion_category,
    delete_promotion_product,
    delete_promotion_location
)

app_name = 'promotions'

urlpatterns = [
    # === Endpoints de consulta ===#
    path('active/', list_active_promotions, name='active_promotions'),
    path('active/products/', list_promotions_active_products,
         name='active_promotions_products'),
    path('active/categories/', list_categories_with_active_promotions,
         name='active_promotions_categories'),

    # === Endpoints de creación ===#
    path('admin/create/', create_promotion, name='create_promotion'),
    path('admin/rules/create/', create_rule, name='create_rule'),
    path('admin/products/create/', create_promotion_product,
         name='create_promotion_product'),
    path('admin/categories/create/', create_promotion_category,
         name='create_promotion_category'),
    path('admin/locations/create/', create_promotion_location,
         name='create_promotion_location'),

    # === Endpoints de actualización ===#
    path('admin/<int:promotion_id>/update/',
         update_promotion, name='update_promotion'),
    path('admin/rules/<int:rule_id>/update/', update_rule, name='update_rule'),

    # === Endpoints de eliminación ===#
    path('admin/<int:promotion_id>/delete/',
         delete_promotion, name='delete_promotion'),
    path('admin/rules/<int:rule_id>/delete/', delete_rule, name='delete_rule'),
    path('admin/<int:promotion_id>/categories/<int:category_id>/delete/',
         delete_promotion_category, name='delete_promotion_category'),
    path('admin/<int:promotion_id>/products/<int:product_id>/delete/',
         delete_promotion_product, name='delete_promotion_product'),
    path('admin/<int:promotion_id>/locations/<int:location_id>/delete/',
         delete_promotion_location, name='delete_promotion_location'),
]
