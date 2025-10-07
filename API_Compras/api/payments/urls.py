from django.urls import path
from . import views

urlpatterns = [

    path('admin/installments/change-state', view=views.change_state_installment,
         name='change_state_installment_admin'),

    path('admin/installments/<int:pk>', view=views.delete_installments,
         name='delete_installments_admin'),

    path('installments', view=views.InstallmentViewSet.as_view(),
         name='list_installments'),

    path('installments/detail', view=views.get_installment_detail,
         name='get_installment_detail'),

    path('installments/pay', view=views.pay,
         name='pay_installment'),

    path('payments', view=views.get_all_payments,
         name='get_all_payments'),

]
