from django.apps import AppConfig
from django.contrib.auth import get_user_model
from django.db.utils import OperationalError, ProgrammingError


class EstoqueConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "estoque"
    verbose_name = "Estoque"

    def ready(self):
        """
        Cria um superusuário automaticamente se não existir.
        Necessário no Render Free (não há acesso ao shell).
        """
        try:
            User = get_user_model()

            if not User.objects.filter(username="admin").exists():
                User.objects.create_superuser(
                    username="admin",
                    email="admin@admin.com",
                    password="admin123"
                )
                print("✔ Superusuário admin criado automaticamente")

        except (OperationalError, ProgrammingError):
            # Banco ainda não está pronto (migrações não rodaram)
            pass
