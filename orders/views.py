from django.shortcuts import render, redirect
from .models import OrderItem, Order
from .forms import OrderCreateForm
from products.cart import Cart
from .services import calculate_shipping
from django.http import JsonResponse
from .gateway_service import AsaasGateway

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json


def order_create(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('products:home')

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)

            # Lógica de Frete e Marketing
            city = form.cleaned_data.get('city')
            order.shipping_cost = calculate_shipping(city)
            order.utm_source = request.session.get('utm_source')
            order.save()

            # Salva os itens do pedido no banco
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity']
                )

            # --- INTEGRAÇÃO ASAAS ---
            gateway = AsaasGateway()

            # Pegamos o método de pagamento do formulário (Ex: 'PIX' ou 'CREDIT_CARD')
            # Se você ainda não tem esse campo no HTML, ele retornará 'UNDEFINED' por padrão
            payment_method = request.POST.get('payment_method', 'UNDEFINED')

            # 1. Cria a cobrança no Asaas
            payment_response = gateway.create_payment(order, billing_type=payment_method)
            print(f"DEBUG ASAAS PAYMENT: {payment_response}")

            context = {
                'order': order,
                'payment_url': payment_response.get('invoiceUrl'),
                'billing_type': payment_response.get('billingType'),
            }

            # 2. Se for PIX, buscamos o QR Code para renderizar em tela
            if context['billing_type'] == 'PIX':
                pix_data = gateway.get_pix_qr_code(payment_response.get('id'))
                context['pix_data'] = pix_data
                print(f"DEBUG ASAAS PIX: {pix_data}")

            # Limpar o carrinho após o sucesso
            request.session['cart'] = {}
            request.session.modified = True # Ou request.session['cart'] = {}

            return render(request, 'orders/created.html', context)
    else:
        form = OrderCreateForm()

    return render(request, 'orders/create.html', {'cart': cart, 'form': form})

def get_shipping_quote(request):
    city = request.GET.get('city', '')
    shipping_cost = calculate_shipping(city)
    return JsonResponse({
        'shipping_cost': str(shipping_cost),
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