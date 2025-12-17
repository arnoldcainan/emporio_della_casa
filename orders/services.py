from decimal import Decimal


def calculate_shipping(city):
    """
    Simulação de lógica de frete para o Empório Della Casa.
    """
    # Exemplo: Cidades próximas com frete reduzido
    local_cities = ['São Paulo', 'Campinas', 'Jundiaí']

    if city in local_cities:
        return Decimal('15.00')
    else:
        # Frete padrão para outras regiões
        return Decimal('35.00')