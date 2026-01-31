from django.contrib import admin
from .models import Categoria, Produto, Movimentacao


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "criada_em")
    search_fields = ("nome",)
    ordering = ("nome",)


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "codigo_barras", "categoria", "estoque_atual", "preco_venda", "criado_em")
    list_filter = ("categoria",)
    search_fields = ("nome", "codigo_barras")
    ordering = ("nome",)
    list_editable = ("estoque_atual", "preco_venda")
    list_per_page = 25


@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ("data", "tipo", "produto", "quantidade", "observacao")
    list_filter = ("tipo", "data")
    search_fields = ("produto__nome", "produto__codigo_barras", "observacao")
    ordering = ("-data",)
    date_hierarchy = "data"
    list_per_page = 25
