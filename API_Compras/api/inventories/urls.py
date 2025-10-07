from django.urls import path
from . import views

urlpatterns = [
    # === Endpoints de administración (Solo administradores - IsAdminUser) ===#

    path('admin/inventories', view=views.list_inventory_records,
         name='list_inventory_records_admin'),
    path('admin/inventories/', view=views.list_inventory_records,
         name='list_inventory_records_admin_slash'),
    # Tests use singular 'inventory' and path '/admin/inventory/records'
    path('admin/inventory/records', view=views.list_inventory_records,
         name='list_inventory_records_admin_alt'),
    path('admin/inventory/records/', view=views.list_inventory_records,
         name='list_inventory_records_admin_alt_slash'),


    path('admin/inventories/purchase-entry', view=views.purchase_entry,
         name='inventory_purchase_entry'),
    path('admin/inventories/purchase-entry/', view=views.purchase_entry,
         name='inventory_purchase_entry_slash'),
    # Singular alternative used by tests
    path('admin/inventory/purchase-entry', view=views.purchase_entry,
         name='inventory_purchase_entry_alt'),
    path('admin/inventory/purchase-entry/', view=views.purchase_entry,
         name='inventory_purchase_entry_alt_slash'),


    path('admin/inventories/exit-sale', view=views.exit_sale,
         name='inventory_exit_sale'),
    path('admin/inventories/exit-sale/', view=views.exit_sale,
         name='inventory_exit_sale_slash'),
    path('admin/inventory/exit-sale', view=views.exit_sale,
         name='inventory_exit_sale_alt'),
    path('admin/inventory/exit-sale/', view=views.exit_sale,
         name='inventory_exit_sale_alt_slash'),


    path('admin/inventories/transfer', view=views.transfer_in,
         name='inventory_transfer'),
    path('admin/inventories/transfer/', view=views.transfer_in,
         name='inventory_transfer_slash'),
    path('admin/inventory/transfer', view=views.transfer_in,
         name='inventory_transfer_alt'),
    path('admin/inventory/transfer/', view=views.transfer_in,
         name='inventory_transfer_alt_slash'),


    path('admin/inventories/adjustment', view=views.adjustment_in,
         name='inventory_adjustment'),
    path('admin/inventories/adjustment/', view=views.adjustment_in,
         name='inventory_adjustment_slash'),
    path('admin/inventory/adjustment', view=views.adjustment_in,
         name='inventory_adjustment_alt'),
    path('admin/inventory/adjustment/', view=views.adjustment_in,
         name='inventory_adjustment_alt_slash'),


    path('admin/inventories/return-entry', view=views.return_entry,
         name='inventory_return_entry'),
    path('admin/inventories/return-entry/', view=views.return_entry,
         name='inventory_return_entry_slash'),
    path('admin/inventory/return-entry', view=views.return_entry,
         name='inventory_return_entry_alt'),
    path('admin/inventory/return-entry/', view=views.return_entry,
         name='inventory_return_entry_alt_slash'),


    path('admin/inventories/return-output', view=views.return_output,
         name='inventory_return_output'),
    path('admin/inventories/return-output/', view=views.return_output,
         name='inventory_return_output_slash'),
    path('admin/inventory/return-output', view=views.return_output,
         name='inventory_return_output_alt'),
    path('admin/inventory/return-output/', view=views.return_output,
         name='inventory_return_output_alt_slash'),
    path('admin/inventories/<int:pk>', view=views.delete_inventory_record,
         name='delete_inventory_record_admin'),
    path('admin/inventories/<int:pk>/', view=views.delete_inventory_record,
         name='delete_inventory_record_admin_slash'),
    path('admin/inventory/<int:pk>', view=views.delete_inventory_record,
         name='delete_inventory_record_admin_alt'),
    path('admin/inventory/<int:pk>/', view=views.delete_inventory_record,
         name='delete_inventory_record_admin_alt_slash'),

    # === Endpoints públicos (Acceso libre - AllowAny) ===#
    # No hay endpoints públicos definidos actualmente
]
