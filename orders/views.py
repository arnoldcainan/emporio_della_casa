from django.shortcuts import render, redirect
from .models import OrderItem, Order
from .forms import OrderCreateForm
from products.cart import Cart
from .services import calculate_shipping
from django.http import JsonResponse



def order_create(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('products:home')
    if not cart:
        return redirect('products:home')
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)

            city = form.cleaned_data.get('city')
            order.shipping_cost = calculate_shipping(city)

            order.utm_source = request.session.get('utm_source')
            order.save()

            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity']
                )

            # Limpar o carrinho após o sucesso
            request.session['cart'] = {}

            return render(request, 'orders/created.html', {'order': order})
    else:
        form = OrderCreateForm()

    return render(request, 'orders/create.html', {'cart': cart, 'form': form})

def get_shipping_quote(request):
    city = request.GET.get('city', '')
    shipping_cost = calculate_shipping(city)
    return JsonResponse({
        'shipping_cost': str(shipping_cost),
    })