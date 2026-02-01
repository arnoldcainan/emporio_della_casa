from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import Newsletter
import json


def subscribe_newsletter(request):
    if request.method == 'POST':
        try:
            # Pega os dados enviados pelo Javascript
            data = json.loads(request.body)
            email = data.get('email', '').strip().lower()

            # 1. Validação básica se está vazio
            if not email:
                return JsonResponse({'success': False, 'message': 'Por favor, digite um e-mail.'})

            # 2. Validação de formato (ex: tem @, tem .com)
            try:
                validate_email(email)
            except ValidationError:
                return JsonResponse({'success': False, 'message': 'Formato de e-mail inválido.'})

            # 3. Verifica duplicidade e Salva
            if Newsletter.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'message': 'Você já faz parte da nossa lista VIP!'})

            Newsletter.objects.create(email=email)
            return JsonResponse({'success': True, 'message': 'Bem-vindo(a) à nossa Adega!'})

        except Exception as e:
            return JsonResponse({'success': False, 'message': 'Erro ao processar inscrição.'}, status=500)

    return JsonResponse({'success': False, 'message': 'Método não permitido.'}, status=405)