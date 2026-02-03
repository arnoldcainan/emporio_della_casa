from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import OrderItem, Order, ShippingRate
from .forms import OrderCreateForm
from financial.models import Enrollment
from products.cart import Cart
from .services import calculate_shipping
from django.http import JsonResponse
from .gateway_service import AsaasGateway
from coupons.models import Coupon
from django.utils import timezone

from django.shortcuts import get_object_or_404, redirect
from django.conf import settings
import requests

from django.contrib.auth import login
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
import json


def order_create(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('products:home')

    form = OrderCreateForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            order = form.save(commit=False)

            # --- 1. LÓGICA DE CUPOM ---
            coupon_id = request.session.get('coupon_id')
            if coupon_id:
                try:
                    coupon = Coupon.objects.get(id=coupon_id, active=True,
                                                valid_from__lte=timezone.now(),
                                                valid_to__gte=timezone.now())
                    order.coupon = coupon
                    order.discount = coupon.discount
                    coupon.usage_count += 1
                    coupon.save()
                except Coupon.DoesNotExist:
                    order.coupon = None
                    order.discount = 0
                    request.session['coupon_id'] = None

            # --- 2. LÓGICA DE FRETE (AGORA FORA DO BLOCO DO CUPOM) ---

            state_uf = form.cleaned_data.get('state').strip().upper()
            selected_method = request.POST.get('shipping_method')

            try:
                from .models import ShippingRate
                rate = ShippingRate.objects.get(state__iexact=state_uf)

                # Valores padrão (Safety First)
                order.shipping_method = 'pac'
                order.shipping_cost = 0

                # Lógica de Prioridade: Só aceita se o valor existir (is not None) no banco

                # Caso 1: Escolheu SEDEX e SEDEX existe para esse estado
                if selected_method == 'sedex' and rate.sedex_cost is not None:
                    order.shipping_cost = rate.sedex_cost
                    order.shipping_method = 'sedex'

                # Caso 2: Escolheu Transportadora e ela existe
                elif selected_method == 'delivery' and rate.delivery_cost is not None:
                    order.shipping_cost = rate.delivery_cost
                    order.shipping_method = 'delivery'

                # Caso 3: Escolheu PAC (ou fallback padrão) e PAC existe
                elif rate.pac_cost is not None:
                    order.shipping_cost = rate.pac_cost
                    order.shipping_method = 'pac'

                # Caso 4 (Emergência): Se PAC for None (ex: estado só tem Sedex), pega o que tiver
                else:
                    if rate.sedex_cost is not None:
                        order.shipping_cost = rate.sedex_cost
                        order.shipping_method = 'sedex'
                    elif rate.delivery_cost is not None:
                        order.shipping_cost = rate.delivery_cost
                        order.shipping_method = 'delivery'

            except ShippingRate.DoesNotExist:
                form.add_error('state', f"Logística indisponível para {state_uf}.")
                return render(request, 'orders/create.html', {'cart': cart, 'form': form})

            # --- 3. SALVAMENTO FINAL ---
            order.state = state_uf
            order.save()

            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity']
                )

            # --- 4. PAGAMENTO ASAAS ---
            try:
                gateway = AsaasGateway()
                payment_response = gateway.create_payment(order, billing_type='UNDEFINED')
                payment_url = payment_response.get('invoiceUrl')
            except Exception as e:
                # Se der erro no Asaas, não quebramos o site, mas logamos
                print(f"Erro ao gerar pagamento Asaas: {e}")
                payment_url = None  # Ou redirecionar para página de erro

            cart.clear()
            request.session['coupon_id'] = None

            return render(request, 'orders/created.html', {
                'order': order,
                'payment_url': payment_url
            })
        else:
            print(f"ERROS DO FORMULÁRIO: {form.errors}")

    return render(request, 'orders/create.html', {'cart': cart, 'form': form})


def get_shipping_quote(request):
    state_uf = request.GET.get('city', '').strip().upper()
    try:
        from .models import ShippingRate
        rate = ShippingRate.objects.get(state__iexact=state_uf)

        # Cria a lista de opções dinamicamente
        options = []

        # Só adiciona PAC se tiver preço e prazo cadastrados
        if rate.pac_cost is not None and rate.pac_days is not None:
            options.append({
                'id': 'pac',
                'name': 'PAC',
                'cost': float(rate.pac_cost),
                'days': rate.pac_days
            })

        # Só adiciona SEDEX se tiver preço e prazo
        if rate.sedex_cost is not None and rate.sedex_days is not None:
            options.append({
                'id': 'sedex',
                'name': 'SEDEX',
                'cost': float(rate.sedex_cost),
                'days': rate.sedex_days
            })

        # Só adiciona Transportadora se tiver preço e prazo
        if rate.delivery_cost is not None and rate.delivery_days is not None:
            options.append({
                'id': 'delivery',
                'name': 'Transportadora',
                'cost': float(rate.delivery_cost),
                'days': rate.delivery_days
            })

        # Se não sobrou nenhuma opção válida (ex: cadastrou o estado mas deixou tudo em branco)
        if not options:
            return JsonResponse({'success': False, 'message': 'Nenhuma modalidade de envio disponível para este Estado.'})

        return JsonResponse({
            'success': True,
            'options': options
        })

    except ShippingRate.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Região não atendida.'})


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
            external_ref = payment.get('externalReference')

            CONFIRMATION_EVENTS = ['PAYMENT_RECEIVED', 'PAYMENT_CONFIRMED']

            if event in CONFIRMATION_EVENTS and external_ref:

                # --- TENTATIVA 1: Tenta achar como ORDER ---
                try:
                    order = Order.objects.get(id=external_ref)

                    # Atualiza Status do Pedido
                    if not order.paid:
                        order.paid = True
                        order.status = 'paid'  # Certifique-se que 'paid' existe no seu STATUS_CHOICES ou use 'processing'/'shipped'
                        order.save()
                        print(f"✅ Webhook: Pedido {order.id} processado como ORDER.")

                    # Libera cursos vinculados à Order
                    try:
                        # Busca usuário pelo e-mail do pedido (mais seguro que order.user)
                        student_user = User.objects.get(email=order.email)

                        # AQUI ESTÁ O PULO DO GATO:
                        # Como seu model tem related_name='items', usamos .items.all()
                        for item in order.items.all():
                            if item.course:
                                enrollment, created = Enrollment.objects.get_or_create(
                                    student=student_user,
                                    course=item.course,
                                    defaults={'status': 'paid'}
                                )
                                if not created or enrollment.status != 'paid':
                                    enrollment.status = 'paid'
                                    enrollment.save()
                                print(f"🎓 Curso '{item.course.title}' liberado para {student_user.email}")

                    except User.DoesNotExist:
                        print(f"⚠️ Usuário com email {order.email} não encontrado.")

                    return JsonResponse({'status': 'order_processed'})

                except (Order.DoesNotExist, ValueError):
                    # --- TENTATIVA 2: Enrollment (Legado) ---
                    try:
                        enrollment = Enrollment.objects.get(id=external_ref)
                        if enrollment.status != 'paid':
                            enrollment.status = 'paid'
                            enrollment.save()

                            send_mail(
                                f'Acesso Liberado: {enrollment.course.title}',
                                'Seu pagamento foi confirmado.',
                                settings.DEFAULT_FROM_EMAIL,
                                [enrollment.student.email],
                                fail_silently=True
                            )
                        return JsonResponse({'status': 'enrollment_processed'})
                    except (Enrollment.DoesNotExist, ValueError):
                        print(f"❌ ERRO: Referência {external_ref} não encontrada.")

            return JsonResponse({'status': 'received'})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# No seu arquivo orders/views.py
def track_orders(request):
    email = request.GET.get('email')
    orders = None

    if email:
        # Normaliza o e-mail da busca para minúsculo
        email_normalized = email.lower().strip()

        # Busca no banco usando o e-mail normalizado
        orders = Order.objects.filter(
            email__iexact=email_normalized  # __iexact ignora maiúsculas/minúsculas no banco
        ).prefetch_related('items__product').order_by('-created')

    return render(request, 'orders/track.html', {
        'orders': orders,
        'email': email
    })


def apply_coupon(request):
    now = timezone.now()
    # Adicionamos .strip() para remover espaços acidentais
    code = request.POST.get('coupon_code', '').strip()

    if not code:
        return JsonResponse({'success': False, 'message': 'Digite um código'})

    try:
        # O __iexact já resolve a questão de Maiúsculas/Minúsculas
        coupon = Coupon.objects.get(code__iexact=code,
                                    valid_from__lte=now,
                                    valid_to__gte=now,
                                    active=True)
        request.session['coupon_id'] = coupon.id
        return JsonResponse({'success': True, 'discount': coupon.discount})
    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Cupom inválido ou expirado'})

def fale_conosco(request):
    return render(request, 'pages/fale_conosco.html')

def trocas_devolucoes(request):
    return render(request, 'pages/trocas.html')

def envios_prazos(request):
    return render(request, 'pages/envios.html')

def winehunters(request):
    """Exibe a página institucional sobre a curadoria de vinhos."""
    return render(request, 'pages/winehunters.html')


from .forms import CustomUserCreationForm  # Importe o novo formulário


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Salva o usuário no banco local
            user = form.save()

            # Especificamos o backend para o Django 6.0 não dar erro 500
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            messages.success(request, f'Bem-vindo, {user.first_name}!')

            # Redireciona para a URL correta
            return redirect('courses:course_list')
    else:
        form = CustomUserCreationForm()

    # Renderiza o template na pasta que você organizou
    return render(request, 'registration/register.html', {'form': form})

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})


# orders/views.py

def process_payment(request, order_id):
    # Busca o pedido 22 que acabamos de criar
    order = get_object_or_404(Order, id=order_id)
    print(f"--- PROCESSANDO PAGAMENTO ASAAS PARA PEDIDO: {order.id} ---")

    try:
        # O AsaasGateway já tem a lógica de criar o cliente se ele não existir
        gateway = AsaasGateway()

        # Chamamos o método que gera a cobrança
        payment_response = gateway.create_payment(order)

        if 'invoiceUrl' in payment_response:
            print(f"✅ Sucesso Asaas! URL Gerada: {payment_response.get('invoiceUrl')}")
            # Redireciona o aluno para a página oficial de pagamento do Asaas
            return redirect(payment_response.get('invoiceUrl'))
        else:
            print(f"❌ ERRO RETORNADO PELO ASAAS: {payment_response}")
            messages.error(request, f"Erro no gateway: {payment_response.get('errors', 'Dados inválidos')}")

    except Exception as e:
        print(f"❌ EXCEÇÃO NO PROCESSAMENTO: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, "Falha na comunicação com o sistema de pagamentos.")

    return redirect('courses:course_list')


# orders/views.py

@login_required
def finalize_course_order(request, course_id):
    print(f"--- INICIANDO FINALIZAÇÃO DE CURSO (ID: {course_id}) ---")
    if request.method == 'POST':
        try:
            from courses.models import Course
            course = get_object_or_404(Course, id=course_id)

            full_name = request.POST.get('full_name', '')
            name_parts = full_name.split(' ', 1)
            f_name = name_parts[0]
            l_name = name_parts[1] if len(name_parts) > 1 else 'Sobrenome'

            # REMOVIDO 'user=request.user' pois o campo não existe no seu models.py
            order = Order.objects.create(
                first_name=f_name,
                last_name=l_name,
                email=request.user.email,  # Identificamos o comprador pelo e-mail
                phone=request.POST.get('phone'),
                address="Acesso Digital",
                postal_code="00000000",
                city="Digital",
                state="SP",
                shipping_cost=0.00,
                paid=False
            )
            print(f"✅ Pedido {order.id} criado com sucesso.")

            OrderItem.objects.create(
                order=order,
                course=course,
                product=None,
                price=course.price,
                quantity=1
            )

            return redirect('orders:process_payment', order_id=order.id)

        except Exception as e:
            print(f"❌ ERRO CRÍTICO NO POST: {str(e)}")
            import traceback
            traceback.print_exc()
            return HttpResponse(f"Erro interno: {e}", status=500)

    return redirect('courses:course_list')