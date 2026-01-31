from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect


# 🔥 PERSONALIZAÇÃO DO ADMIN DJANGO
admin.site.site_header = "Administração da Adega"
admin.site.site_title = "Admin Adega"
admin.site.index_title = "Painel Administrativo da Adega"


def redirect_home(request):
    # redireciona SOMENTE a raiz "/"
    return redirect("entrada_codigo")


urlpatterns = [
    path("admin/", admin.site.urls),

    # 🔥 Rotas do app estoque (PRIMEIRO)
    path("", include("estoque.urls")),

    # 🔁 Redirect APENAS para "/"
    path("", redirect_home),
]
