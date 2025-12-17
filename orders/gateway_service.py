import requests
from datetime import datetime, timedelta
from django.conf import settings

class AsaasGateway:
    def __init__(self):
        self.api_key = settings.ASAAS_API_KEY
        self.api_url = settings.ASAAS_API_URL
        self.headers = {
            'access_token': self.api_key,
            'Content-Type': 'application/json'
        }

    def create_payment(self, order):
        """
        Gera uma cobrança via PIX no Asaas para o pedido enviado.
        """
        due_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')

        # O Asaas espera a chave 'value', não 'amount'
        payload = {
            "billingType": "PIX",
            "value": float(order.get_total_cost()),  # CORREÇÃO AQUI
            "description": f"Pedido #{order.id} - Empório Della Casa",
            "customer": self.get_or_create_customer(order),
            "dueDate": due_date,
            "externalReference": str(order.id)
        }

        response = requests.post(f"{self.api_url}/payments", json=payload, headers=self.headers)
        return response.json()

    def get_or_create_customer(self, order):
        """
        Busca o cliente pelo e-mail. Se não encontrar, cria um novo.
        """
        # 1. Tentar buscar o cliente existente por e-mail
        search_url = f"{self.api_url}/customers?email={order.email}"
        search_response = requests.get(search_url, headers=self.headers)
        search_data = search_response.json()

        # Se encontrou o cliente na lista 'data', retorna o ID do primeiro
        if search_data.get('data'):
            return search_data['data'][0]['id']

        # 2. Se não encontrou, criar um novo
        customer_data = {
            "name": f"{order.first_name} {order.last_name}",
            "email": order.email,
            "cpfCnpj": "35745569000",  # Use um CPF válido para testes
            "mobilePhone": "12997201332",
            "notificationDisabled": True  # Evita que o Asaas envie e-mails de teste ao cliente
        }

        response = requests.post(f"{self.api_url}/customers", json=customer_data, headers=self.headers)
        data = response.json()

        if 'id' in data:
            return data['id']

        # Log de erro caso a criação falhe (ajuda muito na depuração)
        print(f"ERRO AO CRIAR CLIENTE: {data}")
        return None