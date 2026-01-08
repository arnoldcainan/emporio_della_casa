from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
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

            # 1. LOGICA DE CUPOM (Mantida)
            coupon_id = request.session.get('coupon_id')
            if coupon_id:
                try:
                    # Validamos data e atividade novamente antes de salvar o pedido
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
                    request.session['coupon_id'] = None  # Limpa cupom inválido

            # 2. LOGICA DE FRETE (Lendo o novo campo state)
            state_uf = form.cleaned_data.get('state').strip().upper()  # Pega a UF vinda do BuscaCEP
            selected_method = request.POST.get('shipping_method')  # 'pac', 'sedex' ou 'delivery'

            try:
                from .models import ShippingRate
                rate = ShippingRate.objects.get(state__iexact=state_uf)
                # Salva o identificador do método para o seu controle logístico
                order.shipping_method = selected_method

                if selected_method == 'sedex':
                    order.shipping_cost = rate.sedex_cost
                elif selected_method == 'delivery':
                    order.shipping_cost = rate.delivery_cost
                else:
                    order.shipping_cost = rate.pac_cost
                    order.shipping_method = 'pac'

            except ShippingRate.DoesNotExist:
                form.add_error('state', f"Logística indisponível para {state_uf}.")
                return render(request, 'orders/create.html', {'cart': cart, 'form': form})

            # Salva o estado no pedido também
            order.state = state_uf
            order.save()  # Agora salva tudo

            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity']
                )

            # 4. PAGAMENTO ASAAS
            gateway = AsaasGateway()
            payment_response = gateway.create_payment(order, billing_type='UNDEFINED')
            payment_url = payment_response.get('invoiceUrl')

            cart.clear()
            request.session['coupon_id'] = None

            return render(request, 'orders/created.html', {
                'order': order,
                'payment_url': payment_url
            })
        else:
            # DEBUG: Se o código chegar aqui, imprima os erros no terminal do seu PC
            print(f"ERROS DO FORMULÁRIO: {form.errors}")

    return render(request, 'orders/create.html', {'cart': cart, 'form': form})


def get_shipping_quote(request):
    state_uf = request.GET.get('city', '').strip().upper()
    try:
        from .models import ShippingRate
        rate = ShippingRate.objects.get(state__iexact=state_uf)

        return JsonResponse({
            'success': True,
            'options': [
                {'id': 'pac', 'name': 'PAC', 'cost': float(rate.pac_cost), 'days': rate.pac_days},
                {'id': 'sedex', 'name': 'SEDEX', 'cost': float(rate.sedex_cost), 'days': rate.sedex_days},
                {'id': 'delivery', 'name': 'Transportadora', 'cost': float(rate.delivery_cost),
                 'days': rate.delivery_days},
            ]
        })
    except ShippingRate.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Região não atendida.'})


@csrf_exempt
def asaas_webhook(request):
    if request.method == 'POST':
        token_recebido = request.headers.get('asaas-access-token')
        if token_recebido != settings.ASAAS_WEBHOOK_TOKEN:
            return JsonResponse({'error': 'Unauthorized'}, status=401)

        try:
            data = json.loads(request.body)
            event = data.get('event')
            payment = data.get('payment', {})

            # O externalReference agora é sempre o ID do Pedido (Order)
            order_id = payment.get('externalReference')
            CONFIRMATION_EVENTS = ['PAYMENT_RECEIVED', 'PAYMENT_CONFIRMED']

            if event in CONFIRMATION_EVENTS and order_id:
                try:
                    # 1. Busca o pedido no banco
                    order = Order.objects.get(id=order_id)

                    if not order.paid:
                        order.paid = True
                        order.save()
                        print(f"✅ Pedido {order.id} marcado como pago.")

                        # 2. Varre os itens para liberar cursos se houver
                        for item in order.items.all():
                            if item.course:  # Se o item do pedido for um curso
                                enrollment, created = Enrollment.objects.get_or_create(
                                    student=order.user,
                                    course=item.course,
                                    defaults={'status': 'paid'}
                                )
                                if not created:
                                    enrollment.status = 'paid'
                                    enrollment.save()


                            elif item.product:
                                # Aqui você pode adicionar lógica específica para vinhos (ex: baixar estoque)
                                print(f"🍷 Vinho '{item.product.name}' processado no pedido.")

                except Order.DoesNotExist:
                    print(f"❌ Erro: Pedido {order_id} não encontrado.")

            return JsonResponse({'status': 'received'})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

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