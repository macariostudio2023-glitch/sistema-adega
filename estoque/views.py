from datetime import datetime, time
from decimal import Decimal, ROUND_HALF_UP
import csv
import calendar

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

def _money(value):
    return _to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def get_adega_atual(request):
    adega, _ = Adega.objects.get_or_create(id=1, defaults={"nome": "Adega Principal"})
    return adega

# =========================
# ENTRADA (BUSCA E CONFIRMAÇÃO)
# =========================
@login_required
def entrada_codigo_barras(request):
    adega = get_adega_atual(request)
    produto = None
    codigo = ""

    if request.method == "POST":
        codigo = request.POST.get("codigo_barras", "").strip()
        confirmar = request.POST.get("confirmar") # Verifica se clicou no botão verde

        if codigo:
            try:
                produto = Produto.objects.get(adega=adega, codigo_barras=codigo)
                
                # SÓ SALVA SE O USUÁRIO CLICOU EM CONFIRMAR (BOTÃO)
                if confirmar:
                    qtd_raw = request.POST.get("quantidade", "1").strip()
                    quantidade = int(qtd_raw) if qtd_raw and qtd_raw.isdigit() else 1
                    
                    Movimentacao.objects.create(
                        adega=adega, produto=produto, tipo="ENTRADA",
                        quantidade=quantidade, data=timezone.now()
                    )
                    messages.success(request, f"✅ Estoque atualizado: {produto.nome} (+{quantidade})")
                    return redirect("entrada_codigo")
                
                # Se apenas bipou, ele localiza o produto e exibe na tela para conferir
                else:
                    messages.info(request, f"Produto encontrado: {produto.nome}")

            except Produto.DoesNotExist:
                # Se o produto não existe, manda cadastrar
                return redirect(f"/novo-produto/?codigo={codigo}&voltar=/entrada-codigo/")
    
    return render(request, "estoque/entrada_codigo.html", {"produto": produto, "codigo": codigo})

# =========================
# SAÍDA / VENDA
# =========================
@login_required
def saida_codigo_barras(request):
    adega = get_adega_atual(request)
    if request.method == "POST":
        codigo = request.POST.get("codigo_barras", "").strip()
        qtd_raw = request.POST.get("quantidade", "").strip()
        quantidade = int(qtd_raw) if qtd_raw and qtd_raw.isdigit() else 1

        if codigo:
            try:
                produto = Produto.objects.get(adega=adega, codigo_barras=codigo)
                with transaction.atomic():
                    produto.refresh_from_db()
                    if produto.estoque_atual < quantidade:
                        messages.error(request, f"❌ Estoque insuficiente: {produto.estoque_atual}")
                    else:
                        Movimentacao.objects.create(
                            adega=adega, produto=produto, tipo="SAIDA",
                            quantidade=quantidade, data=timezone.now()
                        )
                        messages.success(request, f"✅ Venda realizada: {produto.nome}")
                return redirect("saida_codigo")
            except Produto.DoesNotExist:
                return redirect(f"/novo-produto/?codigo={codigo}&voltar=/saida-codigo/")
    return render(request, "estoque/saida_codigo.html")

# =========================
# CADASTRO E RELATÓRIOS
# =========================
@login_required
def novo_produto(request):
    adega = get_adega_atual(request)
    codigo_bipado = request.GET.get("codigo", "").strip()
    voltar = request.GET.get("voltar", "home")

    if request.method == "POST":
        try:
            Produto.objects.create(
                adega=adega,
                nome=request.POST.get("nome"),
                codigo_barras=request.POST.get("codigo_barras"),
                categoria=request.POST.get("categoria", "Geral"),
                preco_custo=_to_decimal(request.POST.get("preco_custo")),
                preco_venda=_to_decimal(request.POST.get("preco_venda")),
                estoque_atual=int(request.POST.get("estoque_atual") or 0)
            )
            messages.success(request, "✅ Produto cadastrado!")
            return redirect(voltar)
        except Exception as e:
            messages.error(request, f"Erro ao salvar: {e}")
            
    return render(request, "estoque/novo_produto.html", {"codigo": codigo_bipado})

@login_required
def relatorios(request):
    adega = get_adega_atual(request)
    itens = Movimentacao.objects.filter(adega=adega).exclude(tipo="ENTRADA").order_by("-data")[:50]
    return render(request, "estoque/relatorios.html", {"itens": itens})

@login_required
def estoque_baixo(request):
    adega = get_adega_atual(request)
    produtos = Produto.objects.filter(adega=adega, estoque_atual__lte=5)
    return render(request, "estoque/estoque_baixo.html", {"produtos": produtos})

@login_required
def vendas_periodo(request):
    return relatorios(request)

def home(request):
    return redirect("entrada_codigo")

# =========================
# ADMIN GATE
# =========================
@csrf_exempt
@require_POST
def admin_gate_check(request):
    if request.POST.get("senha") == settings.ADMIN_GATE_PASSWORD:
        request.session["admin_gate_ok"] = True
        return JsonResponse({"ok": True})
    return JsonResponse({"ok": False}, status=401)

@login_required
def admin_gate_logout(request):
    request.session.pop("admin_gate_ok", None)
    return redirect("home")

@login_required
def limpar_relatorio(request):
    if request.session.get("admin_gate_ok"):
        Movimentacao.objects.filter(adega=get_adega_atual(request)).exclude(tipo="ENTRADA").delete()
        messages.success(request, "Relatório limpo!")
    return redirect("relatorios")