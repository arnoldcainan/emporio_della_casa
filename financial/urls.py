from django.urls import path
from . import views

app_name = 'financial'

urlpatterns = [
    path('checkout/<int:course_id>/', views.checkout, name='checkout'),
    path('pagamento/sucesso/', views.payment_success, name='success'),
    path('checkout/<int:course_id>/', views.checkout, name='checkout'),
    # path('webhook/', views.asaas_webhook, name='webhook'),

]