from decimal import Decimal


# orders/services.py ou onde estiver sua lógica de frete
def calculate_shipping(city):
    # Exemplo de lógica para teste
    if not city:
        return 0
    if "São Paulo" in city:
        return 15.00
    return 30.00