from datetime import datetime, time
from decimal import Decimal, ROUND_HALF_UP
import csv

from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .models import Adega, Produto, Movimentacao
from .forms import (
    EntradaCodigoBarrasForm,
    SaidaCodigoBarrasForm,
    NovoProdutoPorCodigoForm,
    FiltroEstoqueBaixoForm,
)

# =========================
# HELPERS
# =========================
def _to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))

def _money(value: Decimal) -> Decimal:
    return _to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def _range_dia(uma_data):
    tz = timezone.get_current_timezone()
    inicio = timezone.make_aware(datetime.combine(uma_data, time.min), tz)
    fim = timezone.make_aware(datetime.combine(uma_data, time.max), tz)
    return inicio, fim


# =========================
# ADEGA ATUAL (FIXA)
# =========================
def get_adega_atual(request):
    adega, _ = Adega.objects.get_or_create(
        id=1,
        defaults={"nome": "Adega Principal"}
    )
    return adega


# =========================
# HOME
# =========================
def home(request):
    return redirect("entrada_codigo")


# =========================
# ENTRADA
# =========================
def entrada_codigo_barras(request):
    adega = get_adega_atual(request)
    form = EntradaCodigoBarrasForm(request.POST or None)

    if request.method == "POST":
        if not form.is_valid():
            messages.error(request, f"Form inválido: {form.errors.as_text()}")
            return render(request, "estoque/entrada_codigo.html", {"form": form})

        codigo = form.cleaned_data["codigo_barras"].strip()
        quantidade = form.cleaned_data["quantidade"]

        try:
            produto = Produto.objects.get(adega=adega, codigo_barras=codigo)
        except Produto.DoesNotExist:
            return redirect(f"/novo-produto/?codigo={codigo}&voltar=/entrada-codigo/")

        Movimentacao.objects.create(
            adega=adega,
            produto=produto,
            tipo="ENTRADA",
            quantidade=quantidade,
            data=timezone.now(),
            observacao="Entrada via leitor de código de barras"
        )

        valor_total = _money(_to_decimal(quantidade) * _to_decimal(produto.preco_custo))
        messages.success(request, f"✅ Entrada registrada!\n{produto.nome}\nR$ {valor_total}")
        form = EntradaCodigoBarrasForm()

    return render(request, "estoque/entrada_codigo.html", {"form": form})


# =========================
# SAÍDA
# =========================
def saida_codigo_barras(request):
    adega = get_adega_atual(request)
    form = SaidaCodigoBarrasForm(request.POST or None)

    if request.method == "POST":
        if not form.is_valid():
            messages.error(request, f"Form inválido: {form.errors.as_text()}")
            return render(request, "estoque/saida_codigo.html", {"form": form})

        codigo = form.cleaned_data["codigo_barras"].strip()
        quantidade = form.cleaned_data["quantidade"]

        try:
            produto = Produto.objects.get(adega=adega, codigo_barras=codigo)
        except Produto.DoesNotExist:
            return redirect(f"/novo-produto/?codigo={codigo}&voltar=/saida-codigo/")

        with transaction.atomic():
            produto.refresh_from_db()
            if produto.estoque_atual < quantidade:
                messages.error(request, f"Estoque insuficiente. Atual: {produto.estoque_atual}")
                return render(request, "estoque/saida_codigo.html", {"form": form})

            Movimentacao.objects.create(
                adega=adega,
                produto=produto,
                tipo="SAIDA",
                quantidade=quantidade,
                data=timezone.now(),
                observacao="Saída via leitor de código de barras"
            )

        valor_total = _money(_to_decimal(quantidade) * _to_decimal(produto.preco_venda))
        messages.success(request, f"✅ Venda registrada!\n{produto.nome}\nR$ {valor_total}")
        form = SaidaCodigoBarrasForm()

    return render(request, "estoque/saida_codigo.html", {"form": form})


# =========================
# RELATÓRIOS / OUTROS
# =========================
def relatorios(request):
    return render(request, "estoque/relatorios.html")


# =========================
# 🔐 PASSO 3 — GATE DO ADMIN (BACKEND)
# =========================
@csrf_exempt
@require_POST
def admin_gate_check(request):
    senha = request.POST.get("senha", "")
    if settings.ADMIN_GATE_PASSWORD and senha == settings.ADMIN_GATE_PASSWORD:
        request.session["admin_gate_ok"] = True
        return JsonResponse({"ok": True})
    return JsonResponse({"ok": False}, status=401)
