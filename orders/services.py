from .models import ShippingRate
from django.core.exceptions import ValidationError

def calculate_shipping(state_uf):
    if not state_uf:
        return 0
    try:
        # Busca a UF enviada pelo BuscaCEP (ex: 'SP')
        rate = ShippingRate.objects.get(state__iexact=state_uf)
        # Retorna o custo da transportadora ou PAC
        return rate.delivery_cost
    except ShippingRate.DoesNotExist:
        # Lança erro para estados não cadastrados na sua planilha
        raise ValidationError(f"Infelizmente não temos logística para {state_uf} ainda.")