from datetime import datetime, time, timedelta

from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, F, Q, DecimalField, ExpressionWrapper
from django.http import JsonResponse

from .models import Adega, Produto, Movimentacao
from .forms import (
    EntradaCodigoBarrasForm,
    SaidaCodigoBarrasForm,
    NovoProdutoPorCodigoForm,
    FiltroEstoqueBaixoForm,
    FiltroPeriodoVendasForm,
)


# =========================
# ADEGA ATUAL (FIXA)
# =========================
def get_adega_atual(request):
    # ✅ No Render o banco começa vazio.
    # Se não existir a Adega id=1, cria automaticamente.
    adega, _ = Adega.objects.get_or_create(
        id=1,
        defaults={"nome": "Adega Principal"}
    )
    return adega


# =========================
# HOME → REDIRECT
# =========================
def home(request):
    return redirect("entrada_codigo")


# =========================
# ENTRADA POR CÓDIGO
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
            # ✅ SEM MENSAGEM DE ERRO (não aparece "Código não encontrado")
            return redirect(f"/novo-produto/?codigo={codigo}&voltar=/entrada-codigo/")

        Movimentacao.objects.create(
            adega=adega,
            produto=produto,
            tipo="ENTRADA",
            quantidade=quantidade,
            observacao="Entrada via leitor de código de barras"
        )

        valor_total = quantidade * produto.preco_custo
        messages.success(
            request,
            f"✅ Entrada registrada com sucesso!\n"
            f"{produto.nome}\n"
            f"R$ {valor_total:.2f}"
        )

        form = EntradaCodigoBarrasForm()

    return render(request, "estoque/entrada_codigo.html", {"form": form})


# =========================
# SAÍDA / VENDA POR CÓDIGO
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
            # ✅ SEM MENSAGEM DE ERRO (não aparece faixa vermelha)
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
                observacao="Saída via leitor de código de barras"
            )

        valor_total = quantidade * produto.preco_venda

        messages.success(
            request,
            f"✅ Venda registrada com sucesso!\n"
            f"{produto.nome}\n"
            f"R$ {valor_total:.2f}"
        )

        form = SaidaCodigoBarrasForm()

    return render(request, "estoque/saida_codigo.html", {"form": form})


# =========================
# NOVO PRODUTO
# =========================
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
# RELATÓRIOS (AUTOMÁTICO + FUNCIONA NO BOTÃO)
# =========================
def relatorios(request):
    adega = get_adega_atual(request)

    hoje = timezone.localdate()
    padrao_inicio = hoje - timedelta(days=7)
    padrao_fim = hoje

    # ✅ AGORA ACEITA GET E POST (isso corrige o "Gerar relatório")
    data_source = request.GET if request.method == "GET" else request.POST
    dados = data_source.copy() if data_source else {}

    if not dados.get("data_inicio"):
        dados["data_inicio"] = padrao_inicio
    if not dados.get("data_fim"):
        dados["data_fim"] = padrao_fim

    form = FiltroPeriodoVendasForm(dados)

    if form.is_valid():
        data_inicio = form.cleaned_data.get("data_inicio") or padrao_inicio
        data_fim = form.cleaned_data.get("data_fim") or padrao_fim
    else:
        data_inicio = padrao_inicio
        data_fim = padrao_fim

    tz = timezone.get_current_timezone()
    inicio = timezone.make_aware(datetime.combine(data_inicio, time.min), tz)
    fim = timezone.make_aware(datetime.combine(data_fim, time.max), tz)

    total_linha_expr = ExpressionWrapper(
        F("quantidade") * F("produto__preco_venda"),
        output_field=DecimalField(max_digits=12, decimal_places=2)
    )

    itens = (
        Movimentacao.objects
        .filter(adega=adega, tipo="SAIDA", data__gte=inicio, data__lte=fim)
        .select_related("produto")
        .annotate(total_linha=total_linha_expr)
        .order_by("-data")
    )

    resumo = {
        "total_itens": itens.aggregate(total=Sum("quantidade"))["total"] or 0,
        "total_vendido": itens.aggregate(total=Sum("total_linha"))["total"] or 0,
        "total_vendas": itens.count(),
    }

    return render(request, "estoque/relatorios.html", {
        "form": form,
        "itens": itens,
        "resumo": resumo,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
    })


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


def vendas_hoje(request):
    adega = get_adega_atual(request)
    hoje = timezone.localdate()

    tz = timezone.get_current_timezone()
    inicio = timezone.make_aware(datetime.combine(hoje, time.min), tz)
    fim = timezone.make_aware(datetime.combine(hoje, time.max), tz)

    itens = (
        Movimentacao.objects
        .filter(adega=adega, tipo="SAIDA", data__gte=inicio, data__lte=fim)
        .select_related("produto")
        .order_by("-data")
    )

    total = itens.aggregate(
        total=Sum(F("quantidade") * F("produto__preco_venda"))
    )["total"] or 0

    return render(request, "estoque/vendas_hoje.html", {
        "hoje": hoje,
        "itens": itens,
        "total": total,
    })


# =========================
# VENDAS POR PERÍODO (AUTOMÁTICO)
# =========================
def vendas_periodo(request):
    adega = get_adega_atual(request)

    hoje = timezone.localdate()
    padrao_inicio = hoje - timedelta(days=7)
    padrao_fim = hoje

    data_source = request.GET if request.method == "GET" else request.POST
    dados = data_source.copy() if data_source else {}

    if not dados.get("data_inicio"):
        dados["data_inicio"] = padrao_inicio
    if not dados.get("data_fim"):
        dados["data_fim"] = padrao_fim

    form = FiltroPeriodoVendasForm(dados)

    if form.is_valid():
        data_inicio = form.cleaned_data.get("data_inicio") or padrao_inicio
        data_fim = form.cleaned_data.get("data_fim") or padrao_fim
    else:
        data_inicio = padrao_inicio
        data_fim = padrao_fim

    tz = timezone.get_current_timezone()
    inicio = timezone.make_aware(datetime.combine(data_inicio, time.min), tz)
    fim = timezone.make_aware(datetime.combine(data_fim, time.max), tz)

    total_linha_expr = ExpressionWrapper(
        F("quantidade") * F("produto__preco_venda"),
        output_field=DecimalField(max_digits=12, decimal_places=2)
    )

    itens = (
        Movimentacao.objects
        .filter(adega=adega, tipo="SAIDA", data__gte=inicio, data__lte=fim)
        .select_related("produto")
        .annotate(total_linha=total_linha_expr)
        .order_by("-data")
    )

    total = itens.aggregate(total=Sum("total_linha"))["total"] or 0
    total_itens = itens.aggregate(total=Sum("quantidade"))["total"] or 0
    numero_vendas = itens.count()

    return render(request, "estoque/vendas_periodo.html", {
        "form": form,
        "itens": itens,
        "total": total,
        "total_itens": total_itens,
        "numero_vendas": numero_vendas,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
    })


# =========================
# CONSULTA DE ESTOQUE (autocomplete / busca)
# =========================
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
            "preco": str(p.preco_venda),
        }
        for p in produtos
    ]

    return JsonResponse(dados, safe=False)
