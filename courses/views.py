from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Course, Lesson, LiveClass, LessonView
from financial.models import Enrollment


@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)

    # --- DEBUG (Opcional, pode manter para testes) ---
    # print(f"--- DEBUG ACESSO CURSO ---")
    # print(f"Usuário: {request.user.username} | Curso: {course.title}")

    # Verifica se o aluno tem matrícula PAGA
    is_enrolled = Enrollment.objects.filter(
        student=request.user,
        course=course,
        status='paid'
    ).exists()


    context = {
        'course': course,
        'is_enrolled': is_enrolled  # Essa variável controla o visual (Vitrine vs Aula)
    }
    return render(request, 'courses/course_detail.html', context)


@login_required
def lesson_detail(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk)
    course = lesson.module.course # Pega o curso dono dessa aula

    # --- 1. CAMADA DE SEGURANÇA (Porteiro) ---
    # Verifica no banco se esse aluno comprou este curso
    is_enrolled = Enrollment.objects.filter(
        student=request.user,
        course=course,
        status='paid'
    ).exists()

    # Se o curso custa dinheiro (> 0) e o aluno NÃO está matriculado:
    if course.price > 0 and not is_enrolled:

        return redirect('financial:checkout', course_id=course.id)


    module_lessons = lesson.module.lessons.all()
    lessons_list = list(module_lessons)

    try:
        current_index = lessons_list.index(lesson)
    except ValueError:
        current_index = 0

    previous_lesson = None
    next_lesson = None

    # Se não for a primeira, pega a anterior
    if current_index > 0:
        previous_lesson = lessons_list[current_index - 1]

    # Se não for a última, pega a próxima
    if current_index < len(lessons_list) - 1:
        next_lesson = lessons_list[current_index + 1]

    context = {
        'lesson': lesson,
        'previous_lesson': previous_lesson,
        'next_lesson': next_lesson,
    }
    return render(request, 'courses/lesson_detail.html', context)


@login_required
def mark_lesson_viewed(request, lesson_id):
    lesson = get_object_or_404(Lesson, pk=lesson_id)

    # Cria o registro se não existir
    LessonView.objects.get_or_create(student=request.user, lesson=lesson)

    return redirect('courses:lesson_detail', pk=lesson_id)

@login_required
def my_courses(request):
    # Busca apenas as matrículas com status 'paid' vinculadas ao usuário atual
    enrollments = Enrollment.objects.filter(
        student=request.user,
        status='paid'
    ).select_related('course') # Otimiza a busca trazendo os dados do curso junto

    return render(request, 'courses/my_courses.html', {
        'enrollments': enrollments
    })