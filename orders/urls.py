from django.urls import path
from . import views

# Isso aqui é o que resolve o erro do KeyError: 'orders'
app_name = 'orders'

urlpatterns = [
    path('finalizar/', views.order_create, name='order_create'),
    path('ajax/get-shipping/', views.get_shipping_quote, name='get_shipping_quote'),
    path('webhook/asaas/', views.asaas_webhook, name='asaas_webhook'),
]