from django.urls import path
from . import views

app_name = 'pages'

urlpatterns = [
    path('newsletter/assinar/', views.subscribe_newsletter, name='subscribe'),
]