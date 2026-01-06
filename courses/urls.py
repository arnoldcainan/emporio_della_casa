from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('meus-cursos/', views.my_courses, name='my_courses'),  # Adicione esta linha
    path('<int:pk>/', views.course_detail, name='detail'),

    # Rota para a sala de aula (ex: /cursos/aula/5/)
    path('aula/<int:pk>/', views.lesson_detail, name='lesson_detail'),
    path('marcar-visto/<int:lesson_id>/', views.mark_lesson_viewed, name='mark_viewed'),
]