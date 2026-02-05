from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),

    # Operação
    path("entrada-codigo/", views.entrada_codigo_barras, name="entrada_codigo"),
    path("saida-codigo/", views.saida_codigo_barras, name="saida_codigo"),
    path("novo-produto/", views.novo_produto, name="novo_produto"),

    # Consulta rápida
    path("consultar-estoque/", views.consultar_estoque, name="consultar_estoque"),

    # Relatórios
    path("relatorios/", views.relatorios, name="relatorios"),
    path("relatorios/estoque-baixo/", views.estoque_baixo, name="estoque_baixo"),
    path("relatorios/vendas-hoje/", views.vendas_hoje, name="vendas_hoje"),
    path("relatorios/vendas-periodo/", views.vendas_periodo, name="vendas_periodo"),

    # Ações do relatório
    path("relatorio/baixar/", views.baixar_relatorio, name="baixar_relatorio"),
    path("relatorio/limpar/", views.limpar_relatorio, name="limpar_relatorio"),

    # 🔐 GATE DO ADMIN
    path("admin-gate-check/", views.admin_gate_check, name="admin_gate_check"),
]