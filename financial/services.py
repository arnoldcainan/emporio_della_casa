import requests
from django.conf import settings
from datetime import datetime, timedelta

# Definição explícita da versão e headers padrão
ASAAS_VERSION = 'v3'


def get_headers():
    """
    Retorna os cabeçalhos padrão exigidos pela API v3 do Asaas.
    """
    return {
        "Content-Type": "application/json",
        "access_token": settings.ASAAS_API_KEY,
        "User-Agent": "Hiancias-System/1.0"  # Boa prática: identificar sua aplicação
    }


def get_base_url():
    """
    Garante que a URL termine com /api/v3 sem duplicar barras.
    """
    base = settings.ASAAS_API_URL.rstrip('/')
    if not base.endswith(ASAAS_VERSION):
        base = f"{base}/{ASAAS_VERSION}" if base.endswith('api') else f"{base}/api/{ASAAS_VERSION}"
    return base


def create_asaas_customer(user, cpf=None):
    url = f"{get_base_url()}/customers"
    headers = get_headers()

    # Tratamento do CPF
    cpf_to_send = cpf or user.profile.cpf
    if cpf_to_send:
        cpf_to_send = cpf_to_send.replace('.', '').replace('-', '')

    print(f"DEBUG SERVICE - CPF Limpo: '{cpf_to_send}'")

    payload = {
        "name": user.get_full_name() or user.username,
        "email": user.email,
        "externalReference": str(user.id),
        "cpfCnpj": cpf_to_send,
        "notificationDisabled": False,  # Opcional: permite Asaas enviar email pro cliente
    }

    try:
        # TENTATIVA 1: CRIAR
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            return response.json().get('id')

        # TENTATIVA 2: SE EXISTE (Erro 400), ATUALIZAR
        if response.status_code == 400:
            error_code = response.json().get('errors', [{}])[0].get('code')

            if error_code == 'invalid_customer' or 'already exists' in response.text:
                # Busca pelo email
                search_response = requests.get(f"{url}?email={user.email}", headers=headers)

                if search_response.status_code == 200:
                    data = search_response.json()
                    if data['data']:
                        existing_id = data['data'][0]['id']

                        # ATUALIZA O CADASTRO EXISTENTE COM O CPF NOVO
                        update_url = f"{url}/{existing_id}"
                        update_response = requests.post(update_url, json=payload, headers=headers)

                        if update_response.status_code == 200:
                            return existing_id
                        else:
                            print(f"DEBUG SERVICE - Falha ao atualizar: {update_response.text}")
                            return None

        print(f"Erro Criação Asaas: {response.text}")
        return None

    except Exception as e:
        print(f"DEBUG SERVICE - EXCEPTION: {e}")
        return None


def create_asaas_payment(customer_id, value, description, external_ref):
    url = f"{get_base_url()}/payments"
    headers = get_headers()

    payload = {
        "customer": customer_id,
        "billingType": "UNDEFINED",  # Permite Pix, Boleto e Cartão
        "value": float(value),
        "dueDate": (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
        "description": description,
        "externalReference": external_ref,
        "postalService": False  # Não enviar pelo correio (para boletos)
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Erro Asaas Pagamento: {response.text}")
            return None
    except Exception as e:
        print(f"Erro Requisição Asaas: {e}")
        return None