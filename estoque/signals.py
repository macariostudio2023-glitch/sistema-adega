import os
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import Adega


@receiver(post_migrate)
def criar_dados_iniciais(sender, **kwargs):
    # roda apenas quando migrar o app "estoque"
    if sender.name != "estoque":
        return

    # cria Adega padrão
    Adega.objects.get_or_create(
        id=1,
        defaults={"nome": "Adega Principal"}
    )

    # cria superusuário automaticamente
    username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
    email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@admin.com")
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "admin123")

    User = get_user_model()
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
