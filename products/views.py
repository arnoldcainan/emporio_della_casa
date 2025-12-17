from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Product
from .cart import Cart


def home(request):
    # Buscamos produtos em destaque primeiro, depois os demais
    products = Product.objects.filter(is_active=True).order_by('-is_featured', '-created_at')
    return render(request, 'home.html', {'products': products})


def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.add(product=product, quantity=1)

    return JsonResponse({
        'cart_count': len(cart),
        'message': f'{product.name} adicionado ao carrinho!'
    })

def cart_detail(request):
    cart = Cart(request)
    return render(request, 'cart_detail.html', {'cart': cart})


from django.shortcuts import redirect


def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    if str(product.id) in cart.cart:
        del cart.cart[str(product.id)]
        cart.save()
    return redirect('products:cart_detail')


def cart_update(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    action = request.POST.get('action')  # 'add' ou 'remove'

    if action == 'add':
        cart.add(product=product, quantity=1)
    elif action == 'remove':
        # Se a quantidade for 1, removemos o item, senão diminuímos
        if cart.cart[str(product.id)]['quantity'] > 1:
            cart.add(product=product, quantity=-1)
        else:
            del cart.cart[str(product.id)]
            cart.save()

    return redirect('products:cart_detail')