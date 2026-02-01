"""
Django settings for adega project.
"""

import os
from pathlib import Path
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-%r^$=wne72==ofh@j(0nb(mzdutu(*cy52cvz1l^6!bh%-u5!7")

# SECURITY WARNING: don't run with debug turned on in production!
# No Render: Configure a variável de ambiente DEBUG como 1 se precisar de ver detalhes do erro
DEBUG = os.getenv("DEBUG", "0") == "1"

# No Render: Configurado para aceitar o domínio do Render ou localhost
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "sistema-adega.onrender.com,localhost,127.0.0.1").split(",")

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # App da adega
    "estoque.apps.EstoqueConfig",
]

# ORDEM CORRETA DOS MIDDLEWARES (Corrigido para evitar Erro 500)
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware", # Serve arquivos estáticos
    "django.contrib.sessions.middleware.SessionMiddleware", # Inicia sessão
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware", # Autenticação (obrigatório antes do Gate)
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    
    # O teu middleware customizado deve vir DEPOIS da autenticação e sessão
    "estoque.middleware.AdminGateMiddleware", 
]

ROOT_URLCONF = 'adega.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'adega.wsgi.application'

# =========================
# DATABASE (PostgreSQL Render / SQLite local)
# =========================
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization (Brasil)
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# =========================
# STATIC FILES (Render + Admin)
# =========================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Configuração para o WhiteNoise servir ficheiros comprimidos
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =========================
# 🔐 ADMIN GATE PASSWORD
# =========================
# Certifica-te de que esta variável está no painel "Environment" do Render
ADMIN_GATE_PASSWORD = os.environ.get("ADMIN_GATE_PASSWORD", "")