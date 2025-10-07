from django.urls import path, re_path
from . import views

urlpatterns = [


    # Endpoints asincrónicos (nuevos)
    path(
        'reports/product-rotation/create/',
        views.create_product_rotation_report,
        name='create-product-rotation-report'
    ),
    path(
        'reports/movements/create/',
        views.create_movements_report,
        name='create-movements-report'
    ),
    path(
        'reports/sales-summary/create/',
        views.create_sales_summary_report,
        name='create-sales-summary-report'
    ),
    path(
        'reports/top-products/create/',
        views.create_top_products_report,
        name='create-top-products-report'
    ),
    path(
        'reports/payment-methods/create/',
        views.create_payment_methods_report,
        name='create-payment-methods-report'
    ),
    path(
        'reports/overdue-installments/create/',
        views.create_overdue_installments_report,
        name='create-overdue-installments-report'
    ),
    path(
        'reports/status/<str:task_id>/',
        views.check_report_status,
        name='check-report-status'
    ),
    path(
        'reports/<int:report_id>/download/',
        views.download_report,
        name='download-report'
    ),
    path(
        'reports/',
        views.list_user_reports,
        name='list-user-reports'
    ),
]
