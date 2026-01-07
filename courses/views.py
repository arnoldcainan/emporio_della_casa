from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Course, Lesson, LiveClass, LessonView
from financial.models import Enrollment
from products.cart import Cart

from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from .models import Course
import io


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


def course_list(request):
    courses = Course.objects.filter(is_active=True) # Assumindo que você tem um campo 'active'
    return render(request, 'courses/course_list.html', {'courses': courses})


@login_required
def add_course_to_cart(request, course_id):
    """
    Adiciona um curso ao carrinho ou libera acesso imediato se for gratuito.
    """
    course = get_object_or_404(Course, id=course_id)

    # --- 1. VERIFICAÇÃO DE MATRÍCULA EXISTENTE ---
    # Evita que o usuário compre ou adicione ao carrinho algo que já possui
    already_enrolled = Enrollment.objects.filter(
        student=request.user,
        course=course,
        status='paid'
    ).exists()

    if already_enrolled:
        messages.info(request, f'Você já possui acesso ao curso "{course.title}".')
        return redirect('courses:detail', pk=course.id)

    # --- 2. FLUXO PARA CURSOS GRATUITOS ---
    if course.price <= 0:
        # Cria a matrícula com status 'paid' imediatamente
        Enrollment.objects.get_or_create(
            student=request.user,
            course=course,
            defaults={'status': 'paid'}
        )
        messages.success(request, f'Inscrição realizada! O curso "{course.title}" já está disponível.')
        # Redireciona direto para a página do curso, pulando o carrinho
        return redirect('courses:detail', pk=course.id)

    # --- 3. FLUXO PARA CURSOS PAGOS ---
    cart = Cart(request)

    # Adicionamos o objeto course.
    # IMPORTANTE: Sua classe Cart.add deve ser capaz de lidar com o objeto Course.
    # Como seu template de carrinho usa 'product.name', e o curso usa 'title',
    # o ajuste no template que fizemos antes (usando |default) é essencial.
    cart.add(product=course, quantity=1)

    messages.success(request, f'O curso "{course.title}" foi adicionado ao seu carrinho.')
    return redirect('products:cart_detail')





@login_required
def emit_certificate(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    user = request.user

    # 1. Criar um buffer para o PDF
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    # 2. Desenhar o fundo (Template do curso)
    if course.certificate_template:
        p.drawImage(course.certificate_template.path, 0, 0, width=width, height=height)

    # 3. Configurar Texto (Nome do Aluno)
    p.setFont("Helvetica-Bold", 30)
    p.drawCentredString(width / 2.0, height / 2.0 + 20, f"{user.first_name} {user.last_name}")

    p.setFont("Helvetica", 18)
    p.drawCentredString(width / 2.0, height / 2.0 - 20, f"Concluiu com êxito o curso {course.title}")

    # 4. Finalizar
    p.showPage()
    p.save()

    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')