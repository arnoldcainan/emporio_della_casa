# core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from orders import views as order_views
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('products.urls', namespace='products')),
    path('coupons/', include('coupons.urls', namespace='coupons')),

    # Adicione esta linha abaixo para registrar o namespace 'orders'
    path('orders/', include('orders.urls', namespace='orders')),
    path('fale-conosco/', order_views.fale_conosco, name='fale_conosco'),
    path('trocas-e-devolucoes/', order_views.trocas_devolucoes, name='trocas'),
    path('prazos-de-entrega/', order_views.envios_prazos, name='envios'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)