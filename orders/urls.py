from django.urls import path
from . import views

# Isso aqui é o que resolve o erro do KeyError: 'orders'
app_name = 'orders'

urlpatterns = [
    path('finalizar/', views.order_create, name='order_create'),
    path('get-shipping-quote/', views.get_shipping_quote, name='get_shipping_quote'),
    path('rastrear/', views.track_orders, name='track_orders'),
    path('webhook/asaas/', views.asaas_webhook, name='asaas_webhook'),
    path('coupons/apply/', views.apply_coupon, name='apply_coupon'),

    path('fale-conosco/', views.fale_conosco, name='fale_conosco'),
    path('trocas-e-devolucoes/', views.trocas_devolucoes, name='trocas'),
    path('prazos-de-entrega/', views.envios_prazos, name='envios'),
    path('winehunters/', views.winehunters, name='winehunters'),

]