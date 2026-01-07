from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('meus-cursos/', views.my_courses, name='my_courses'),
    path('todos/', views.course_list, name='course_list'),
    path('<int:pk>/', views.course_detail, name='detail'),

    path('comprar/<int:course_id>/', views.add_course_to_cart, name='add_to_cart'),

    # Rota para a sala de aula (ex: /cursos/aula/5/)
    path('aula/<int:pk>/', views.lesson_detail, name='lesson_detail'),
    path('marcar-visto/<int:lesson_id>/', views.mark_lesson_viewed, name='mark_viewed'),
path('certificado/<int:course_id>/', views.emit_certificate, name='emit_certificate'),
]