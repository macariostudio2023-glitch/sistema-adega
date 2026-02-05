from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import csv

from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.decorators import login_required

from .models import Adega, Produto, Movimentacao

# =========================
# HELPERS (UTILITÁRIOS)
# =========================
def _to_decimal(value):
    if not value: return Decimal("0.00")
    try:
        return Decimal(str(value).replace(',', '.'))
    except:
        return Decimal("0.00")

def get_adega_atual(request):
    adega, _ = Adega.objects.get_or_create(id=1, defaults={"nome": "Adega Principal"})
    return adega

# =========================
# OPERAÇÃO (ENTRADA E SAÍDA)
# =========================
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
                messages.success(request, f"✅ Estoque: {produto.nome} (+{quantidade})")
                return redirect("entrada_codigo")
        except Produto.DoesNotExist:
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
                with transaction.atomic():
                    produto.refresh_from_db()
                    if produto.estoque_atual < quantidade:
                        messages.error(request, "❌ Estoque insuficiente!")
                    else:
                        Movimentacao.objects.create(adega=adega, produto=produto, tipo="SAIDA", quantidade=quantidade)
                        messages.success(request, f"✅ Venda: {produto.nome}")
                        return redirect("saida_codigo")
        except Produto.DoesNotExist:
            return redirect(f"/novo-produto/?codigo={codigo}&voltar=/saida-codigo/")
    return render(request, "estoque/saida_codigo.html", {"produto": produto, "codigo": codigo})

# =========================
# CONSULTAS E RELATÓRIOS
# =========================
@login_required
def consultar_estoque(request):
    termo = request.GET.get('q', '').strip()
    adega = get_adega_atual(request)
    produtos = Produto.objects.filter(Q(adega=adega) & (Q(nome__icontains=termo) | Q(codigo_barras__icontains=termo)))[:10]
    dados = [{"id": p.id, "nome": p.nome, "codigo": p.codigo_barras, "preco_venda": str(p.preco_venda), "estoque": p.estoque_atual} for p in produtos]
    return JsonResponse(dados, safe=False)

@login_required
def relatorios(request):
    adega = get_adega_atual(request)
    itens = Movimentacao.objects.filter(adega=adega).order_by("-data")[:50]
    return render(request, "estoque/relatorios.html", {"itens": itens})

@login_required
def vendas_hoje(request):
    adega = get_adega_atual(request)
    vendas = Movimentacao.objects.filter(adega=adega, tipo="SAIDA", data__date=timezone.now().date())
    total = sum(v.quantidade * v.produto.preco_venda for v in vendas)
    return render(request, "estoque/vendas_hoje.html", {"vendas": vendas, "total_valor": total})

@login_required
def vendas_periodo(request):
    # Por enquanto, redireciona para o relatório geral ou vendas de hoje
    return vendas_hoje(request)

@login_required
def estoque_baixo(request):
    produtos = Produto.objects.filter(adega=get_adega_atual(request), estoque_atual__lte=5)
    return render(request, "estoque/estoque_baixo.html", {"produtos": produtos})

# =========================
# AÇÕES E SEGURANÇA
# =========================
@login_required
def baixar_relatorio(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatorio_estoque.csv"'
    writer = csv.writer(response)
    writer.writerow(['Produto', 'Tipo', 'Quantidade', 'Data'])
    movs = Movimentacao.objects.filter(adega=get_adega_atual(request)).order_by("-data")
    for m in movs:
        writer.writerow([m.produto.nome, m.tipo, m.quantidade, m.data])
    return response

@login_required
def limpar_relatorio(request):
    if request.session.get("admin_gate_ok"):
        Movimentacao.objects.filter(adega=get_adega_atual(request)).exclude(tipo="ENTRADA").delete()
        messages.success(request, "Relatório limpo!")
    return redirect("relatorios")

@csrf_exempt
@require_POST
def admin_gate_check(request):
    if request.POST.get("senha") == settings.ADMIN_GATE_PASSWORD:
        request.session["admin_gate_ok"] = True
        return JsonResponse({"ok": True})
    return JsonResponse({"ok": False}, status=401)

# =========================
# CADASTRO E HOME
# =========================
@login_required
def novo_produto(request):
    adega = get_adega_atual(request)
    if request.method == "POST":
        Produto.objects.create(
            adega=adega, 
            nome=request.POST.get("nome"), 
            codigo_barras=request.POST.get("codigo_barras"), 
            preco_venda=_to_decimal(request.POST.get("preco_venda")), 
            estoque_atual=int(request.POST.get("estoque_atual") or 0)
        )
        return redirect("entrada_codigo")
    return render(request, "estoque/novo_produto.html", {"codigo": request.GET.get("codigo", "")})

def home(request):
    return redirect("entrada_codigo")