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
from django.core.mail import send_mail
from django.contrib.auth.models import User

# --- IMPORTS CORRIGIDOS ---
from .models import Enrollment  # App Financial
from orders.models import Order  # App Orders
from coupons.models import Coupon  # App Coupons
from .services import create_asaas_customer, create_asaas_payment


@login_required
def checkout(request, course_id):
    course = get_object_or_404(Course, pk=course_id)

    # Preço inicial
    final_price = course.price
    coupon_code = request.session.get('coupon_code')
    coupon_obj = None

    # Lógica de Cupom
    if coupon_code:
        try:
            coupon_obj = Coupon.objects.get(code=coupon_code, active=True)
            if coupon_obj.valid_to and coupon_obj.valid_to < timezone.now():
                del request.session['coupon_code']
                coupon_obj = None
                messages.warning(request, "O cupom expirou.")
            else:
                discount_amount = (final_price * coupon_obj.discount_percent) / 100
                final_price = final_price - discount_amount
        except Coupon.DoesNotExist:
            del request.session['coupon_code']
            messages.error(request, "Cupom inválido.")

    # Cria Matrícula Provisória
    enrollment, created = Enrollment.objects.get_or_create(
        student=request.user,
        course=course,
        defaults={'amount': final_price}
    )

    if enrollment.status == 'paid':
        return redirect('courses:detail', pk=course.id)

    if request.method == 'POST':
        if 'apply_coupon' in request.POST:
            code = request.POST.get('coupon_code').strip().upper()
            try:
                cupom = Coupon.objects.get(code=code, active=True)
                if cupom.valid_to and cupom.valid_to < timezone.now():
                    messages.error(request, "Este cupom já venceu.")
                else:
                    request.session['coupon_code'] = code
                    messages.success(request, f"Cupom {code} aplicado com sucesso!")
            except Coupon.DoesNotExist:
                messages.error(request, "Cupom não encontrado.")
            return redirect('financial:checkout', course_id=course.id)

        elif 'remove_coupon' in request.POST:
            if 'coupon_code' in request.session:
                del request.session['coupon_code']
                messages.info(request, "Cupom removido.")
            return redirect('financial:checkout', course_id=course.id)

        elif 'finish_payment' in request.POST:
            enrollment.amount = final_price
            enrollment.save()

            cpf_input = request.POST.get('cpf')
            customer_id = create_asaas_customer(request.user, cpf=cpf_input)

            if not customer_id:
                messages.error(request, "Erro no cadastro Asaas.")
                return redirect('financial:checkout', course_id=course.id)

            # AQUI VOCÊ ENVIA O ID DA MATRÍCULA (Enrollment)
            payment_data = create_asaas_payment(
                customer_id=customer_id,
                value=final_price,
                description=f"Curso: {course.title}",
                external_ref=str(enrollment.id)
            )

            if payment_data and 'invoiceUrl' in payment_data:
                enrollment.asaas_payment_id = payment_data['id']
                enrollment.asaas_payment_link = payment_data['invoiceUrl']
                enrollment.save()

                if final_price <= 0:
                    enrollment.status = 'paid'
                    enrollment.save()
                    return redirect('courses:detail', pk=course.id)

                return render(request, 'financial/redirect_asaas.html', {'payment_link': enrollment.asaas_payment_link})
            else:
                messages.error(request, "Erro ao gerar cobrança.")

    context = {
        'course': course,
        'final_price': final_price,
        'coupon': coupon_obj,
        'enrollment': enrollment,
        'user': request.user
    }
    return render(request, 'financial/checkout.html', context)


def payment_success(request):
    return render(request, 'financial/dashboard.html')


@csrf_exempt
def asaas_webhook(request):
    """
    Webhook Híbrido: Aceita pagamentos via Order (Carrinho) e via Enrollment (Checkout Direto)
    """
    if request.method == 'POST':
        token_recebido = request.headers.get('asaas-access-token')
        if token_recebido != settings.ASAAS_WEBHOOK_TOKEN:
            return JsonResponse({'error': 'Unauthorized'}, status=401)

        try:
            data = json.loads(request.body)
            event = data.get('event')
            payment = data.get('payment', {})
            external_ref = payment.get('externalReference')  # Pode ser ID de Order OU de Enrollment

            CONFIRMATION_EVENTS = ['PAYMENT_RECEIVED', 'PAYMENT_CONFIRMED']

            if event in CONFIRMATION_EVENTS and external_ref:

                # --- TENTATIVA 1: Tenta achar como ORDER (Fluxo novo) ---
                try:
                    order = Order.objects.get(id=external_ref)
                    if not order.paid:
                        order.paid = True
                        order.status = 'paid'
                        order.save()
                        print(f"✅ Webhook: Pedido {order.id} processado como ORDER.")

                    # Libera cursos vinculados à Order
                    try:
                        student_user = User.objects.get(email=order.email)
                        for item in order.items.all():
                            if item.course:
                                enrollment, _ = Enrollment.objects.get_or_create(
                                    student=student_user,
                                    course=item.course,
                                    defaults={'status': 'paid'}
                                )
                                enrollment.status = 'paid'
                                enrollment.save()
                    except User.DoesNotExist:
                        pass  # Usuário não encontrado

                    return JsonResponse({'status': 'order_processed'})

                except (Order.DoesNotExist, ValueError):
                    # --- TENTATIVA 2: Tenta achar como ENROLLMENT (Fluxo antigo deste checkout) ---
                    # Se falhou ao buscar Order, tenta buscar Enrollment direto
                    try:
                        enrollment = Enrollment.objects.get(id=external_ref)
                        if enrollment.status != 'paid':
                            enrollment.status = 'paid'
                            enrollment.save()
                            print(f"✅ Webhook: Matrícula {enrollment.id} processada como ENROLLMENT.")

                            # Envia e-mail simples
                            send_mail(
                                f'Acesso Liberado: {enrollment.course.title}',
                                'Seu pagamento foi confirmado.',
                                settings.DEFAULT_FROM_EMAIL,
                                [enrollment.student.email],
                                fail_silently=True
                            )
                        return JsonResponse({'status': 'enrollment_processed'})
                    except (Enrollment.DoesNotExist, ValueError):
                        print(f"❌ ERRO: Referência {external_ref} não encontrada nem como Order nem como Enrollment.")

            return JsonResponse({'status': 'received'})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)