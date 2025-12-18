from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Coupon


@require_POST
def apply_coupon(request):
    now = timezone.now()
    code = request.POST.get('coupon_code')

    try:
        # Busca o cupom ignorando maiúsculas/minúsculas e verifica validade
        coupon = Coupon.objects.get(
            code__iexact=code,
            valid_from__lte=now,
            valid_to__gte=now,
            active=True
        )
        # Armazena o ID do cupom na sessão do usuário
        request.session['coupon_id'] = coupon.id

        return JsonResponse({
            'success': True,
            'discount': coupon.discount
        })

    except Coupon.DoesNotExist:
        # Limpa o cupom da sessão se o código for inválido
        request.session['coupon_id'] = None
        return JsonResponse({
            'success': False,
            'message': 'Cupom inválido ou expirado'
        })