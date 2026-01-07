from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Course, Lesson, LiveClass, LessonView
from .forms import CourseEnrollmentForm
from financial.models import Enrollment
from products.cart import Cart
from orders.models import Order, OrderItem

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
def buy_now(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Verifica se já possui acesso
    if Enrollment.objects.filter(student=request.user, course=course, status='paid').exists():
        messages.info(request, "Você já possui acesso a este curso.")
        return redirect('courses:detail', pk=course.id)

    # Fluxo Gratuito
    if course.price <= 0:
        Enrollment.objects.get_or_create(student=request.user, course=course, defaults={'status': 'paid'})
        return redirect('courses:detail', pk=course.id)

    # Fluxo Pago: Redireciona para preencher CPF/Telefone
    return render(request, 'courses/finalize_enrollment.html', {
        'course': course,
        'form': CourseEnrollmentForm(initial={'full_name': request.user.get_full_name()})
    })





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


@login_required
def finalize_course_order(request, course_id):
    if request.method == 'POST':
        course = get_object_or_404(Course, id=course_id)

        # 1. Cria o Pedido (Order) com dados do formulário
        # Usamos os campos que o AsaasGateway precisará para criar o cliente
        order = Order.objects.create(
            user=request.user,
            first_name=request.POST.get('full_name'),
            email=request.user.email,
            phone=request.POST.get('phone'),
            total_amount=course.price,
            status='processing'
        )

        # 2. Vincula o curso ao item do pedido
        OrderItem.objects.create(
            order=order,
            course=course,
            product=None,  # Permitido pelo ajuste no models.py
            price=course.price,
            quantity=1
        )

        # 3. Chama o processamento de pagamento existente
        return redirect('orders:process_payment', order_id=order.id)

    return redirect('courses:course_list')