# core/middleware.py

class UTMMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Lista de parâmetros que queremos rastrear
        utm_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content']

        # Verifica se algum parâmetro está na URL
        for param in utm_params:
            value = request.GET.get(param)
            if value:
                # Salva na sessão do usuário
                request.session[param] = value

        response = self.get_response(request)
        return response