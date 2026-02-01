from django.contrib import admin
from django.urls import path, include

# 🔥 PERSONALIZAÇÃO DO ADMIN DJANGO
admin.site.site_header = "Administração da Adega"
admin.site.site_title = "Admin Adega"
admin.site.index_title = "Painel Administrativo da Adega"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("estoque.urls")),
]
