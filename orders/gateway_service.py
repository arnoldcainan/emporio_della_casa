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

    def create_payment(self, order, billing_type='UNDEFINED'):
        """
        Gera uma cobrança via PIX no Asaas para o pedido enviado.
        """
        due_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')

        # O Asaas espera a chave 'value', não 'amount'
        payload = {
            "billingType": billing_type,
            "value": float(order.get_total_cost()),
            "description": f"Pedido #{order.id} - Empório Della Casa",
            "customer": self.get_or_create_customer(order),
            "dueDate": due_date,
            "externalReference": str(order.id)
        }

        response = requests.post(f"{self.api_url}/payments", json=payload, headers=self.headers)
        return response.json()

    def get_or_create_customer(self, order, cpf_form=None):
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
            "cpfCnpj": cpf_form if cpf_form else "68516656039",
            "mobilePhone": order.phone,
            "notificationDisabled": True
        }

        response = requests.post(f"{self.api_url}/customers", json=customer_data, headers=self.headers)
        data = response.json()

        if 'id' in data:
            return data['id']

        # Log de erro caso a criação falhe (ajuda muito na depuração)
        print(f"ERRO AO CRIAR CLIENTE: {data}")
        return None


    def get_pix_qr_code(self, payment_id):
        """Busca o QR Code e a chave copia e cola de uma cobrança Pix"""
        url = f"{self.api_url}/payments/{payment_id}/pixQrCode"
        response = requests.get(url, headers=self.headers)

        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"ERRO ASAAS QRCODE: {response.text}")
                return None
        except Exception as e:
            print(f"EXCEÇÃO AO BUSCAR QRCODE: {e}")
            return None