from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.home, name='home'),
    path('add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('carrinho/', views.cart_detail, name='cart_detail'),
    path('carrinho/remover/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('carrinho/atualizar/<int:product_id>/', views.cart_update, name='cart_update'),
]