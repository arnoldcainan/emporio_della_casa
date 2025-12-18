import os
import django

# Define as configurações do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User

def create_admin():
    # Busca as variáveis do ambiente do Railway
    username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
    email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@email.com')
    password = os.getenv('DJANGO_SUPERUSER_PASSWORD')

    if not password:
        print("❌ ERRO: A variável DJANGO_SUPERUSER_PASSWORD não foi definida no Railway.")
        return

    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, email, password)
        print(f"✅ Superusuário '{username}' criado com sucesso!")
    else:
        print(f"ℹ️ O usuário '{username}' já existe.")

if __name__ == "__main__":
    create_admin()