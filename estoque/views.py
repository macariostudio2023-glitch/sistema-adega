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
from django.contrib.auth.decorators import login_required  # ✅ Importado para segurança

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
# ENTRADA POR CÓDIGO
# =========================
@login_required
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
        messages.success(
            request,
            f"✅ Entrada registrada!\n{produto.nome}\nR$ {valor_total}"
        )

        form = EntradaCodigoBarrasForm()

    return render(request, "estoque/entrada_codigo.html", {"form": form})


# =========================
# SAÍDA POR CÓDIGO
# =========================
@login_required
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
                messages.error(
                    request,
                    f"Estoque insuficiente. Atual: {produto.estoque_atual}"
                )
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
        messages.success(
            request,
            f"✅ Venda registrada!\n{produto.nome}\nR$ {valor_total}"
        )

        form = SaidaCodigoBarrasForm()

    return render(request, "estoque/saida_codigo.html", {"form": form})


# =========================
# NOVO PRODUTO
# =========================
@login_required
def novo_produto(request):
    adega = get_adega_atual(request)

    codigo = request.GET.get("codigo", "").strip()
    voltar = request.GET.get("voltar", "/entrada-codigo/")

    if not codigo:
        messages.error(request, "Código de barras não informado.")
        return render(request, "estoque/novo_produto.html", {"form": None})

    if Produto.objects.filter(adega=adega, codigo_barras=codigo).exists():
        messages.success(request, "Esse código já existe nesta adega.")
        return redirect(voltar)

    if request.method == "POST":
        form = NovoProdutoPorCodigoForm(request.POST)
        if form.is_valid():
            produto = Produto.objects.create(
                adega=adega,
                codigo_barras=form.cleaned_data["codigo_barras"],
                nome=form.cleaned_data["nome"],
                categoria=form.cleaned_data["categoria"],
                preco_custo=form.cleaned_data["preco_custo"],
                preco_venda=form.cleaned_data["preco_venda"],
                estoque_atual=form.cleaned_data["estoque_inicial"],
            )

            messages.success(request, f"✅ Produto cadastrado: {produto.nome}")
            return render(
                request,
                "estoque/produto_cadastrado.html",
                {"produto": produto, "voltar": voltar}
            )
    else:
        form = NovoProdutoPorCodigoForm(initial={"codigo_barras": codigo})

    return render(request, "estoque/novo_produto.html", {"form": form})


# =========================
# RELATÓRIOS
# =========================
@login_required
def relatorios(request):
    adega = get_adega_atual(request)

    hoje = timezone.localdate()
    inicio_mes = hoje.replace(day=1)

    dt_inicio, _ = _range_dia(inicio_mes)
    _, dt_fim = _range_dia(hoje)

    itens_qs = (
        Movimentacao.objects
        .filter(adega=adega, data__gte=dt_inicio, data__lte=dt_fim)
        .exclude(tipo__iexact="ENTRADA")
        .select_related("produto")
        .order_by("-data")
    )

    itens = []
    total_vendido = Decimal("0.00")
    total_itens = 0

    for m in itens_qs:
        preco = _money(_to_decimal(m.produto.preco_venda))
        qtd = int(m.quantidade)
        total_linha = _money(preco * _to_decimal(qtd))

        itens.append({
            "data": m.data,
            "produto_nome": m.produto.nome,
            "quantidade": qtd,
            "preco_venda": preco,
            "total_linha": total_linha,
            "tipo": m.tipo,
        })

        total_vendido += total_linha
        total_itens += qtd

    resumo = {
        "total_vendido": _money(total_vendido),
        "total_itens": total_itens,
        "total_vendas": itens_qs.count(),
    }

    return render(request, "estoque/relatorios.html", {
        "itens": itens,
        "resumo": resumo,
        "inicio_mes": inicio_mes,
        "hoje": hoje,
    })


# =========================
# ESTOQUE BAIXO
# =========================
@login_required
def estoque_baixo(request):
    adega = get_adega_atual(request)
    form = FiltroEstoqueBaixoForm(request.GET or None)
    limite = form.cleaned_data["limite"] if form.is_valid() else 5

    produtos = Produto.objects.filter(
        adega=adega,
        estoque_atual__lte=limite
    ).order_by("estoque_atual", "nome")

    return render(request, "estoque/estoque_baixo.html", {
        "form": form,
        "limite": limite,
        "produtos": produtos,
    })


# =========================
# CONSULTA DE ESTOQUE
# =========================
@login_required
def consultar_estoque(request):
    adega = get_adega_atual(request)
    termo = request.GET.get("q", "").strip()

    produtos = (
        Produto.objects
        .filter(adega=adega)
        .filter(
            Q(nome__icontains=termo) |
            Q(codigo_barras__icontains=termo)
        )
        .order_by("nome")[:10]
    )

    dados = [
        {
            "nome": p.nome,
            "codigo": p.codigo_barras,
            "estoque": p.estoque_atual,
            "preco": str(_money(_to_decimal(p.preco_venda))),
        }
        for p in produtos
    ]

    return JsonResponse(dados, safe=False)


# =========================
# VENDAS HOJE
# =========================
@login_required
def vendas_hoje(request):
    adega = get_adega_atual(request)

    hoje = timezone.localdate()
    inicio, fim = _range_dia(hoje)

    itens_qs = (
        Movimentacao.objects
        .filter(adega=adega, data__gte=inicio, data__lte=fim)
        .exclude(tipo__iexact="ENTRADA")
        .select_related("produto")
        .order_by("-data")
    )

    itens = []
    total = Decimal("0.00")

    for m in itens_qs:
        preco = _money(_to_decimal(m.produto.preco_venda))
        qtd = int(m.quantidade)
        total_linha = _money(preco * _to_decimal(qtd))

        itens.append({
            "data": m.data,
            "produto_nome": m.produto.nome,
            "quantidade": qtd,
            "preco_venda": preco,
            "total_linha": total_linha,
            "tipo": m.tipo,
        })

        total += total_linha

    return render(request, "estoque/vendas_hoje.html", {
        "hoje": hoje,
        "itens": itens,
        "total": _money(total),
        "total_vendas": itens_qs.count(),
    })


@login_required
def vendas_periodo(request):
    return relatorios(request)


# =========================
# BAIXAR RELATÓRIO CSV (MELHORADO + HORA CERTA)
# =========================
@login_required
def baixar_relatorio(request):
    adega = get_adega_atual(request)

    hoje = timezone.localdate()
    inicio_mes = hoje.replace(day=1)

    dt_inicio, _ = _range_dia(inicio_mes)
    _, dt_fim = _range_dia(hoje)

    itens_qs = (
        Movimentacao.objects
        .filter(adega=adega, data__gte=dt_inicio, data__lte=dt_fim)
        .exclude(tipo__iexact="ENTRADA")
        .select_related("produto")
        .order_by("data")
    )

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="relatorio_{inicio_mes.strftime("%Y_%m")}.csv"'
    )

    # ✅ BOM para Excel abrir acentos corretamente
    response.write("\ufeff")

    # ✅ separador ; (Excel pt-BR não bagunça)
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Data", "Produto", "Quantidade", "Preço", "Total", "Tipo"])

    for m in itens_qs:
        preco = _money(_to_decimal(m.produto.preco_venda))
        qtd = int(m.quantidade)
        total_linha = _money(preco * _to_decimal(qtd))

        dt = timezone.localtime(m.data) if m.data else None

        writer.writerow([
            dt.strftime("%d/%m/%Y %H:%M") if dt else "",
            m.produto.nome,
            qtd,
            f"{preco:.2f}".replace(".", ","),
            f"{total_linha:.2f}".replace(".", ","),
            m.tipo,
        ])

    return response


# =========================
# LIMPAR RELATÓRIO
# =========================
@login_required
@require_POST
def limpar_relatorio(request):
    adega = get_adega_atual(request)

    hoje = timezone.localdate()
    inicio_mes = hoje.replace(day=1)

    dt_inicio, _ = _range_dia(inicio_mes)
    _, dt_fim = _range_dia(hoje)

    apagados, _ = (
        Movimentacao.objects
        .filter(adega=adega, data__gte=dt_inicio, data__lte=dt_fim)
        .exclude(tipo__iexact="ENTRADA")
        .delete()
    )

    messages.success(
        request,
        f"✅ Relatório limpo. Registros removidos: {apagados}"
    )
    return redirect("relatorios")


# =========================
# 🔐 GATE DO ADMIN (MANTIDO)
# =========================
@csrf_exempt
@require_POST
def admin_gate_check(request):
    senha = request.POST.get("senha", "").strip()

    if settings.ADMIN_GATE_PASSWORD and senha == settings.ADMIN_GATE_PASSWORD:
        request.session["admin_gate_ok"] = True
        return JsonResponse({"ok": True}, status=200)

    return JsonResponse({"ok": False}, status=401)
