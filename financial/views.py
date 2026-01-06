import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from courses.models import Course, Lesson
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from .models import Enrollment,Coupon
from .services import create_asaas_customer, create_asaas_payment
from django.core.mail import send_mail


@login_required
def checkout(request, course_id):
    course = get_object_or_404(Course, pk=course_id)

    # Preço inicial (pode ser alterado pelo cupom)
    final_price = course.price
    coupon_code = request.session.get('coupon_code')  # Tenta pegar da sessão
    coupon_obj = None

    # Lógica de validação do cupom (se existir na sessão)
    if coupon_code:
        try:
            coupon_obj = Coupon.objects.get(code=coupon_code, active=True)
            # Verifica validade (se tiver data limite)
            if coupon_obj.valid_to and coupon_obj.valid_to < timezone.now():
                del request.session['coupon_code']
                coupon_obj = None
                messages.warning(request, "O cupom expirou.")
            else:
                # Aplica o desconto
                discount_amount = (final_price * coupon_obj.discount_percent) / 100
                final_price = final_price - discount_amount
        except Coupon.DoesNotExist:
            del request.session['coupon_code']
            messages.error(request, "Cupom inválido.")

    # Cria/Recupera matrícula (ainda sem salvar o valor final, pois pode mudar)
    enrollment, created = Enrollment.objects.get_or_create(
        student=request.user,
        course=course,
        defaults={'amount': final_price}  # Valor padrão
    )

    if enrollment.status == 'paid':
        return redirect('courses:detail', pk=course.id)

    if request.method == 'POST':
        # --- CENÁRIO 1: APLICAR CUPOM ---
        if 'apply_coupon' in request.POST:
            code = request.POST.get('coupon_code').strip().upper()
            try:
                # Verifica se existe e está ativo
                cupom = Coupon.objects.get(code=code, active=True)

                # Verifica data
                if cupom.valid_to and cupom.valid_to < timezone.now():
                    messages.error(request, "Este cupom já venceu.")
                else:
                    # Salva na sessão e recarrega a página
                    request.session['coupon_code'] = code
                    messages.success(request, f"Cupom {code} aplicado com sucesso!")

            except Coupon.DoesNotExist:
                messages.error(request, "Cupom não encontrado.")

            return redirect('financial:checkout', course_id=course.id)

        # --- CENÁRIO 2: REMOVER CUPOM ---
        elif 'remove_coupon' in request.POST:
            if 'coupon_code' in request.session:
                del request.session['coupon_code']
                messages.info(request, "Cupom removido.")
            return redirect('financial:checkout', course_id=course.id)

        # --- CENÁRIO 3: FINALIZAR PAGAMENTO (CÓDIGO ANTERIOR) ---
        elif 'finish_payment' in request.POST:
            # Atualiza o valor final na matrícula antes de enviar pro Asaas
            enrollment.amount = final_price
            enrollment.save()

            # ... (Seu código de CPF e Asaas que já estava aqui) ...
            # ... COPIE E COLE AQUI A PARTE DO CPF E CREATE_ASAAS ...

            # ATENÇÃO: Na chamada create_asaas_payment, use 'final_price' em vez de 'course.price'
            # payment_data = create_asaas_payment(..., value=final_price, ...)

            # --- COLE AQUI O RESTANTE DA LÓGICA DO PASSO ANTERIOR (CPF, Asaas) ---
            # Vou resumir para não ficar gigante, mas você mantém sua lógica de CPF:

            cpf_input = request.POST.get('cpf')
            if cpf_input:
                # ... lógica de salvar cpf ...
                pass

            customer_id = create_asaas_customer(request.user, cpf=cpf_input)
            if not customer_id:
                messages.error(request, "Erro no cadastro Asaas.")
                return redirect('financial:checkout', course_id=course.id)

            # Gera cobrança com o PREÇO COM DESCONTO
            payment_data = create_asaas_payment(
                customer_id=customer_id,
                value=final_price,  # <--- IMPORTANTE: Usar o preço calculado
                description=f"Curso: {course.title}",
                external_ref=str(enrollment.id)
            )

            if payment_data and 'invoiceUrl' in payment_data:
                enrollment.asaas_payment_id = payment_data['id']
                enrollment.asaas_payment_link = payment_data['invoiceUrl']
                enrollment.save()

                # Se o preço for ZERO (100% desconto), libera direto!
                if final_price <= 0:
                    enrollment.status = 'paid'
                    enrollment.save()
                    return redirect('courses:detail', pk=course.id)

                return render(request, 'financial/redirect_asaas.html', {'payment_link': enrollment.asaas_payment_link})
            else:
                messages.error(request, "Erro ao gerar cobrança.")

    context = {
        'course': course,
        'final_price': final_price,  # Manda o preço calculado
        'coupon': coupon_obj,  # Manda o objeto do cupom (para mostrar o nome)
        'enrollment': enrollment,
        'user': request.user
    }
    return render(request, 'financial/checkout.html', context)

def payment_success(request):
    return render(request, 'financial/dashboard.html')



@csrf_exempt
def asaas_webhook(request):
    if request.method == 'POST':
        # Validação do Token (Header: asaas-access-token)
        token_recebido = request.headers.get('asaas-access-token')
        if token_recebido != settings.ASAAS_WEBHOOK_TOKEN:
            return JsonResponse({'error': 'Unauthorized'}, status=401)

        try:
            data = json.loads(request.body)

            # DEBUG: Ver o que o Asaas mandou
            # print(f"PAYLOAD ASAAS: {data}")

            event = data.get('event')
            payment = data.get('payment', {})

            # ID da Matrícula
            enrollment_id = payment.get('externalReference')

            # Tipos de eventos que confirmam o pagamento no Asaas v3
            CONFIRMATION_EVENTS = ['PAYMENT_RECEIVED', 'PAYMENT_CONFIRMED']

            if event in CONFIRMATION_EVENTS:
                if enrollment_id:
                    try:
                        enrollment = Enrollment.objects.get(id=enrollment_id)

                        if enrollment.status != 'paid':
                            enrollment.status = 'paid'
                            enrollment.save()

                            # --- ENVIA E-MAIL DE BOAS-VINDAS ---
                            subject = f'Pagamento Aprovado: {enrollment.course.title}'
                            message = f"""
                                                    Olá {enrollment.student.first_name},

                                                    Seu pagamento foi confirmado com sucesso!
                                                    Você já pode acessar o curso "{enrollment.course.title}" na sua plataforma.

                                                    Bons estudos!
                                                    Equipe Hiâncias
                                                    """
                            try:
                                send_mail(
                                    subject,
                                    message,
                                    settings.DEFAULT_FROM_EMAIL,
                                    [enrollment.student.email],
                                    fail_silently=True,
                                )
                                print(f"E-mail de confirmação enviado para {enrollment.student.email}")
                            except Exception as e:
                                print(f"Erro ao enviar email: {e}")

                    except Enrollment.DoesNotExist:
                        print(f"ERRO: Matrícula {enrollment_id} não encontrada.")

            return JsonResponse({'status': 'received'})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

    return JsonResponse({'error': 'Method not allowed'}, status=405)