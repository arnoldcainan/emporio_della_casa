from django.urls import path
from . import views # Isso importa o arquivo views.py da mesma pasta

app_name = 'coupons'

urlpatterns = [
    path('apply/', views.apply_coupon, name='apply'),
]