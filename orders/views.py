from django.shortcuts import render, redirect
from .models import OrderItem, Order
from .forms import OrderCreateForm
from products.cart import Cart
from .services import calculate_shipping
from django.http import JsonResponse
from .gateway_service import AsaasGateway
from coupons.models import Coupon
from django.utils import timezone

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json


def order_create(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('products:home')

    form = OrderCreateForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            order = form.save(commit=False)

            # 1. LOGICA DE CUPOM (Tracking)
            coupon_id = request.session.get('coupon_id')
            if coupon_id:
                try:
                    coupon = Coupon.objects.get(id=coupon_id, active=True)
                    order.coupon = coupon
                    order.discount = coupon.discount

                    # Incrementa o contador de uso do cupom
                    coupon.usage_count += 1
                    coupon.save()
                except Coupon.DoesNotExist:
                    # Se o cupom sumiu ou foi desativado, o pedido segue sem ele
                    order.coupon = None
                    order.discount = 0

            # 2. LOGICA DE FRETE
            city = form.cleaned_data.get('city')
            order.shipping_cost = calculate_shipping(city)

            # Salva o pedido inicial para gerar o ID
            order.save()

            # 3. SALVA OS ITENS DO CARRINHO
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity']
                )

            # 4. INTEGRAÇÃO ASAAS (Pagamento via Link)
            gateway = AsaasGateway()
            # O billing_type='UNDEFINED' permite que o Asaas mostre Pix, Cartão e Boleto
            payment_response = gateway.create_payment(order, billing_type='UNDEFINED')
            payment_url = payment_response.get('invoiceUrl')

            # 5. LIMPEZA E FINALIZAÇÃO
            cart.clear()
            request.session['coupon_id'] = None  # Limpa o cupom da sessão

            # Renderiza a página intermediária de "Redirecionamento Seguro"
            return render(request, 'orders/created.html', {
                'order': order,
                'payment_url': payment_url
            })

    # Caso seja GET ou formulário inválido
    return render(request, 'orders/create.html', {'cart': cart, 'form': form})

def get_shipping_quote(request):
    city = request.GET.get('city', '')
    shipping_cost = calculate_shipping(city)
    # Retornar como string evita problemas de precisão no JSON
    return JsonResponse({
        'shipping_cost': "{:.2f}".format(shipping_cost),
    })

@csrf_exempt
def asaas_webhook(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        print(f"--- WEBHOOK RECEBIDO ---")
        print(f"JSON: {data}")  # Isso vai mostrar tudo no seu terminal

        event = data.get('event')
        payment = data.get('payment', {})
        external_reference = payment.get('externalReference')

        if event in ['PAYMENT_CONFIRMED', 'PAYMENT_RECEIVED']:
            try:
                # O ID que o Asaas devolve no externalReference deve ser o ID do seu Pedido
                order = Order.objects.get(id=external_reference)
                order.paid = True
                order.save()
                print(f"✅ SUCESSO: Pedido {external_reference} atualizado!")
            except Exception as e:
                print(f"❌ ERRO AO SALVAR: {e}")

        return HttpResponse(status=200)
    return HttpResponse(status=400)


def track_orders(request):
    email = request.GET.get('email')
    orders = None

    if email:
        # Buscamos os pedidos filtrando pelo email e usamos prefetch_related
        # para carregar os vinhos de uma vez só e deixar a página rápida.
        orders = Order.objects.filter(email=email).prefetch_related('items__product').order_by('-created')

    return render(request, 'orders/track.html', {
        'orders': orders,
        'email': email
    })

def apply_coupon(request):
    now = timezone.now()
    code = request.POST.get('coupon_code')
    try:
        coupon = Coupon.objects.get(code__iexact=code,
                                  valid_from__lte=now,
                                  valid_to__gte=now,
                                  active=True)
        request.session['coupon_id'] = coupon.id
        return JsonResponse({'success': True, 'discount': coupon.discount})
    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Cupom inválido'})


def fale_conosco(request):
    return render(request, 'pages/fale_conosco.html')

def trocas_devolucoes(request):
    return render(request, 'pages/trocas.html')

def envios_prazos(request):
    return render(request, 'pages/envios.html')

def winehunters(request):
    """Exibe a página institucional sobre a curadoria de vinhos."""
    return render(request, 'pages/winehunters.html')