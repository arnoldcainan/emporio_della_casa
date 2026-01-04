from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.shortcuts import redirect
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

    # Se a requisição for AJAX (JavaScript Fetch)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'total_items': len(cart),
            'product_name': product.name,
            'message': 'Adicionado com sucesso!'
        })

    # Se for um clique normal (sem JS), redireciona para o carrinho
    return redirect('products:cart_detail')

def cart_detail(request):
    cart = Cart(request)
    return render(request, 'cart_detail.html', {'cart': cart})



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


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    # Busca 4 produtos da mesma categoria, excluindo o atual
    related_products = Product.objects.filter(category=product.category, is_active=True).exclude(id=product.id)[:4]

    return render(request, 'products/product_detail.html', {
        'product': product,
        'related_products': related_products
    })