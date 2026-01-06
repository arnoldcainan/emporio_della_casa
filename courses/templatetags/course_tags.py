from django import template
from courses.models import LessonView, Lesson
from financial.models import Enrollment

register = template.Library()


@register.simple_tag
def course_progress(user, course):
    """
    Retorna a porcentagem de conclusão de um curso para um usuário.
    Uso no HTML: {% course_progress request.user course as percent %}
    """
    if not user.is_authenticated:
        return 0

    # Total de aulas do curso
    total_lessons = Lesson.objects.filter(module__course=course).count()

    if total_lessons == 0:
        return 0

    # Aulas que o usuário viu
    views = LessonView.objects.filter(
        student=user,
        lesson__module__course=course
    ).count()

    # Cálculo da porcentagem
    percent = (views / total_lessons) * 100
    return int(percent)


@register.simple_tag
def is_lesson_viewed(user, lesson):
    """
    Retorna True se o aluno já viu a aula.
    """
    if not user.is_authenticated:
        return False
    return LessonView.objects.filter(student=user, lesson=lesson).exists()

@register.simple_tag
def has_access(user, course):
    """
    Retorna True se o usuário comprou o curso (status='paid').
    """
    if not user.is_authenticated:
        return False
    return Enrollment.objects.filter(student=user, course=course, status='paid').exists()