# orders/urls.py
from django.urls import path
from . import views

# Isso aqui é o que resolve o erro do KeyError: 'orders'
app_name = 'orders'

urlpatterns = [
    path('finalizar/', views.order_create, name='order_create'),
]