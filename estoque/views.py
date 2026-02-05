from datetime import datetime
from decimal import Decimal
import csv
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import Adega, Produto, Movimentacao, Categoria

# Helpers
def _to_decimal(value):
    if not value: return Decimal("0.00")
    try:
        return Decimal(str(value).replace(',', '.'))
    except:
        return Decimal("0.00")

def get_adega_atual(request):
    try:
        adega = Adega.objects.first()
        if not adega:
            adega = Adega.objects.create(nome="Minha Adega")
        return adega
    except:
        return None

# Views Operacionais
@login_required
def entrada_codigo_barras(request):
    adega = get_adega_atual(request)
    produto = None
    codigo = request.POST.get("codigo_barras", "").strip()
    acao = request.POST.get("acao")

    if request.method == "POST" and codigo:
        try:
            produto = Produto.objects.get(adega=adega, codigo_barras=codigo)
            if acao == "salvar":
                qtd_raw = request.POST.get("quantidade", "1").strip()
                quantidade = int(qtd_raw) if qtd_raw.isdigit() else 1
                Movimentacao.objects.create(adega=adega, produto=produto, tipo="ENTRADA", quantidade=quantidade)
                messages.success(request, f"✅ Entrada: {produto.nome} (+{quantidade})")
                return redirect("entrada_codigo")
        except Produto.DoesNotExist:
            # Informa que deve voltar para entrada
            return redirect(f"/novo-produto/?codigo={codigo}&voltar=/entrada-codigo/")
    
    return render(request, "estoque/entrada_codigo.html", {"produto": produto, "codigo": codigo})

@login_required
def saida_codigo_barras(request):
    adega = get_adega_atual(request)
    produto = None
    codigo = request.POST.get("codigo_barras", "").strip()
    acao = request.POST.get("acao")

    if request.method == "POST" and codigo:
        try:
            produto = Produto.objects.get(adega=adega, codigo_barras=codigo)
            if acao == "salvar":
                qtd_raw = request.POST.get("quantidade", "1").strip()
                quantidade = int(qtd_raw) if qtd_raw.isdigit() else 1
                if produto.estoque_atual < quantidade:
                    messages.error(request, "❌ Estoque insuficiente!")
                else:
                    Movimentacao.objects.create(adega=adega, produto=produto, tipo="SAIDA", quantidade=quantidade)
                    messages.success(request, f"✅ Venda: {produto.nome}")
                    return redirect("saida_codigo")
        except Produto.DoesNotExist:
            # Informa que deve voltar para SAÍDA
            return redirect(f"/novo-produto/?codigo={codigo}&voltar=/saida-codigo/")
            
    return render(request, "estoque/saida_codigo.html", {"produto": produto, "codigo": codigo})

@login_required
def novo_produto(request):
    adega = get_adega_atual(request)
    categoria, _ = Categoria.objects.get_or_create(nome="Geral")
    
    codigo_url = request.GET.get("codigo", "")
    # Pega o destino de volta da URL. Se não houver, o padrão é entrada.
    onde_voltar = request.GET.get("voltar", "/entrada-codigo/")

    if request.method == "POST":
        Produto.objects.create(
            adega=adega,
            nome=request.POST.get("nome"),
            categoria=categoria,
            codigo_barras=request.POST.get("codigo_barras"),
            preco_custo=_to_decimal(request.POST.get("preco_custo")),
            preco_venda=_to_decimal(request.POST.get("preco_venda")),
            estoque_atual=int(request.POST.get("estoque_atual") or 0)
        )
        # Redireciona para onde o usuário estava antes
        return redirect(onde_voltar)

    return render(request, "estoque/novo_produto.html", {
        "codigo": codigo_url, 
        "voltar": onde_voltar
    })
def home(request): 
    return redirect("entrada_codigo")

# --- COLE ISSO NO FINAL DO SEU estoque/views.py ---

@login_required
def consultar_estoque(request):
    termo = request.GET.get('q', '').strip()
    adega = get_adega_atual(request)
    # Busca por nome ou código de barras
    produtos = Produto.objects.filter(
        Q(adega=adega) & 
        (Q(nome__icontains=termo) | Q(codigo_barras__icontains=termo))
    )[:10]
    
    dados = [{"nome": p.nome, "estoque": p.estoque_atual} for p in produtos]
    return JsonResponse(dados, safe=False)

def home(request):
    return redirect("entrada_codigo")
# ... Resto das views (consultar_estoque, relatorios, etc) permanecem iguais