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
        try:
            data = json.loads(request.body)
            event = data.get('event')
            payment = data.get('payment', {})
            external_reference = payment.get('externalReference')

            # Eventos de confirmação do Asaas
            if event in ['PAYMENT_CONFIRMED', 'PAYMENT_RECEIVED']:
                try:
                    # 1. Atualiza o status do Pedido
                    order = Order.objects.get(id=external_reference)
                    order.paid = True
                    order.save()
                    print(f"✅ Pedido {order.id} pago.")

                    # 2. Varre os itens do pedido em busca de cursos
                    for item in order.items.all():
                        # Se o produto tiver um curso vinculado no models.py
                        if item.product.related_course:
                            course = item.product.related_course

                            # Cria a matrícula liberada (status 'paid')
                            enrollment, created = Enrollment.objects.get_or_create(
                                student=order.user,
                                course=course,
                                defaults={'status': 'paid'}
                            )

                            # Se já existia (ex: boleto vencido e pago depois), força o 'paid'
                            if not created:
                                enrollment.status = 'paid'
                                enrollment.save()

                            print(f"🎓 Curso '{course.title}' liberado para {order.user.email}")

                except Order.DoesNotExist:
                    print(f"❌ Erro: Pedido {external_reference} não encontrado no banco.")
                except Exception as e:
                    print(f"❌ Erro ao processar itens: {e}")

            return HttpResponse(status=200)
        except json.JSONDecodeError:
            return HttpResponse(status=400)

    return HttpResponse(status=405)


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
            return redirect('courses:my_courses')
    else:
        form = CustomUserCreationForm()

    # Renderiza o template na pasta que você organizou
    return render(request, 'registration/register.html', {'form': form})

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})