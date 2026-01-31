from datetime import datetime, time

from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse

from .models import Adega, Produto, Movimentacao
from .forms import (
    EntradaCodigoBarrasForm,
    SaidaCodigoBarrasForm,
    NovoProdutoPorCodigoForm,
    FiltroEstoqueBaixoForm,
)

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
# RELATÓRIO DO MÊS (SIMPLÃO, SEM FORM, FUNCIONA SEMPRE)
# =========================
def relatorios(request):
    adega = get_adega_atual(request)

    hoje = timezone.localdate()
    inicio_mes = hoje.replace(day=1)

    tz = timezone.get_current_timezone()
    dt_inicio = timezone.make_aware(datetime.combine(inicio_mes, time.min), tz)
    dt_fim = timezone.make_aware(datetime.combine(hoje, time.max), tz)

    # ✅ Pega tudo do mês que NÃO é ENTRADA (então pega SAIDA / VENDA / etc.)
    itens_qs = (
        Movimentacao.objects
        .filter(adega=adega, data__gte=dt_inicio, data__lte=dt_fim)
        .exclude(tipo__iexact="ENTRADA")
        .select_related("produto")
        .order_by("-data")
    )

    # ✅ Calcula tudo no Python (mais simples, não depende de annotate / banco)
    itens = []
    total_vendido = 0
    total_itens = 0

    for m in itens_qs:
        preco = float(m.produto.preco_venda)
        qtd = int(m.quantidade)
        total_linha = qtd * preco

        itens.append({
            "data": m.data,
            "produto_nome": m.produto.nome,
            "quantidade": qtd,
            "preco_venda": preco,
            "total_linha": total_linha,
        })

        total_vendido += total_linha
        total_itens += qtd

    resumo = {
        "total_vendido": total_vendido,
        "total_itens": total_itens,
        "total_vendas": len(itens),
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
