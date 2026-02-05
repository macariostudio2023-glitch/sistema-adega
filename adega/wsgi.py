import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adega.settings')

application = get_wsgi_application()

# --- BLOCO DE CRIAÇÃO AUTOMÁTICA DO MACARIO ---
from django.contrib.auth import get_user_model
User = get_user_model()

try:
    if not User.objects.filter(username="Macario").exists():
        User.objects.create_superuser("Macario", "admin@email.com", "Macario@122436")
        print("✅ Usuário Macario criado com sucesso!")
    else:
        print("ℹ️ Usuário Macario já existe.")
except Exception as e:
    print(f"❌ Erro ao criar user: {e}")
# ----------------------------------------------