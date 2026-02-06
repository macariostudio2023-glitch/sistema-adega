import os
from pathlib import Path
import dj_database_url

# Caminho base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# SEGURANÇA
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-chave-temporaria-123")

# DEBUG: True para ver erros no Render. False para produção real.
DEBUG = os.getenv("DEBUG", "True") == "True"

# Domínios permitidos
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "sistema-adega.onrender.com,localhost,127.0.0.1").split(",")

# Apps instalados
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Seu App
    "estoque.apps.EstoqueConfig",
]

# Ordem correta dos Middlewares
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware", # Essencial para o Render
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = 'adega.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'adega.wsgi.application'

# BANCO DE DADOS (Configuração Profissional)
# Usa Postgres no Render (DATABASE_URL) e SQLite localmente
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600
    )
}

# Validação de Senhas
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Localização e Idioma
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# ARQUIVOS ESTÁTICOS
STATIC_URL = "/static/"

# O ajuste definitivo para o Render (usando Path):
STATIC_ROOT = BASE_DIR / "staticfiles"

# Armazenamento otimizado para o Render
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Se você tiver uma pasta 'static' na raiz, adicione isso:
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CONFIGURAÇÕES DE LOGIN
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/entrada-codigo/'
LOGOUT_REDIRECT_URL = '/login/'

# SENHA DO GATE (Vem das variáveis de ambiente do Render)
ADMIN_GATE_PASSWORD = os.getenv("ADMIN_GATE_PASSWORD", "1234")


