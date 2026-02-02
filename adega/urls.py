from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views  # Necessário para o login

# 🔥 PERSONALIZAÇÃO DO ADMIN DJANGO
admin.site.site_header = "Administração da Adega"
admin.site.site_title = "Admin Adega"
admin.site.index_title = "Painel Administrativo da Adega"

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # 🔐 TELA DE LOGIN CUSTOMIZADA
    # O caminho 'estoque/login.html' aponta corretamente para a pasta vista na imagem
    path("login/", auth_views.LoginView.as_view(template_name="estoque/login.html"), name="login"),
    
    # 🚪 ROTA PARA LOGOUT
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # APP DA ADEGA
    path("", include("estoque.urls")),
]