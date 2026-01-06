
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from orders import views as order_views
from django.contrib.auth import views as auth_views

from django.conf.urls.static import static

from django.views.static import serve
from django.urls import re_path

urlpatterns = [
    path('admin/', admin.site.urls),

    # Login e Logout com caminhos explícitos
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Cadastro
    path('cadastro/', order_views.register, name='register'),

    # Recuperação de Senha (seguindo o padrão da pasta registration)
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html'), name='password_reset'),

    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),

    path('password_reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

    # Alteração de Senha (opcional, para área logada)
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change_form.html'), name='password_change'),

    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html'), name='password_change_done'),

    path('', include('products.urls', namespace='products')),
    path('coupons/', include('coupons.urls', namespace='coupons')),

    path('cursos/', include('courses.urls', namespace='courses')),

    path('orders/', include('orders.urls', namespace='orders')),
    path('fale-conosco/', order_views.fale_conosco, name='fale_conosco'),
    path('trocas-e-devolucoes/', order_views.trocas_devolucoes, name='trocas'),
    path('prazos-de-entrega/', order_views.envios_prazos, name='envios'),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)