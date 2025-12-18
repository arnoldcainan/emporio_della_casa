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

    form = OrderCreateForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            order = form.save(commit=False)
            city = form.cleaned_data.get('city')
            order.shipping_cost = calculate_shipping(city)
            order.save()

            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity']
                )

            gateway = AsaasGateway()
            payment_response = gateway.create_payment(order, billing_type='UNDEFINED')
            payment_url = payment_response.get('invoiceUrl')

            cart.clear()
            return render(request, 'orders/created.html', {
                'order': order,
                'payment_url': payment_url
            })

        # Se o form for inválido, o código continua para o return lá embaixo
        # carregando o form com os erros.

    # Esta linha DEVE estar fora do 'if request.method'
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