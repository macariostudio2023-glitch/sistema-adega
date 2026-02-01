from django.urls import path
from .views import (
    home,
    entrada_codigo_barras,
    saida_codigo_barras,
    novo_produto,
    relatorios,
    estoque_baixo,
    vendas_hoje,
    vendas_periodo,
    consultar_estoque,
    baixar_relatorio,
    limpar_relatorio,
    admin_gate_check,   # ✅ ADICIONA ESSE
)

urlpatterns = [
    path("", home, name="home"),

    # Operação
    path("entrada-codigo/", entrada_codigo_barras, name="entrada_codigo"),
    path("saida-codigo/", saida_codigo_barras, name="saida_codigo"),
    path("novo-produto/", novo_produto, name="novo_produto"),

    # Consulta rápida
    path("consultar-estoque/", consultar_estoque, name="consultar_estoque"),

    # Relatórios
    path("relatorios/", relatorios, name="relatorios"),
    path("relatorios/estoque-baixo/", estoque_baixo, name="estoque_baixo"),
    path("relatorios/vendas-hoje/", vendas_hoje, name="vendas_hoje"),
    path("relatorios/vendas-periodo/", vendas_periodo, name="vendas_periodo"),

    # Ações do relatório
    path("relatorio/baixar/", baixar_relatorio, name="baixar_relatorio"),
    path("relatorio/limpar/", limpar_relatorio, name="limpar_relatorio"),

    # 🔐 GATE DO ADMIN (ESSA ROTA ESTAVA FALTANDO)
    path("admin-gate-check/", admin_gate_check, name="admin_gate_check"),
]




