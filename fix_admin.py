import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adega.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
username = 'admin_novo'
email = 'admin@email.com'
password = 'SenhaDificil123@' # Mude esta senha se quiser

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f"✅ Usuario {username} criado com sucesso!")
else:
    user = User.objects.get(username=username)
    user.set_password(password)
    user.save()
    print(f"✅ Senha do usuario {username} foi atualizada!")