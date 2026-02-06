import csv
from datetime import datetime
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import Adega, Produto, Movimentacao, Categoria

# --- HELPERS ---
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

# --- OPERAÇÕES ---
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
                    valor_total = produto.preco_venda * quantidade
                    Movimentacao.objects.create(adega=adega, produto=produto, tipo="SAIDA", quantidade=quantidade)
                    messages.success(request, f"✅ Venda: {produto.nome} | Total: R$ {valor_total:.2f}")
                    return redirect("saida_codigo")
        except Produto.DoesNotExist:
            return redirect(f"/novo-produto/?codigo={codigo}&voltar=/saida-codigo/")
            
    return render(request, "estoque/saida_codigo.html", {"produto": produto, "codigo": codigo})

@login_required
def novo_produto(request):
    adega = get_adega_atual(request)
    categoria, _ = Categoria.objects.get_or_create(nome="Geral")
    codigo_url = request.GET.get("codigo", "")
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
        messages.success(request, "✅ Produto cadastrado com sucesso!")
        return redirect(onde_voltar)

    return render(request, "estoque/novo_produto.html", {"codigo": codigo_url, "voltar": onde_voltar})

# --- CONSULTAS E RELATÓRIOS ---
@login_required
def consultar_estoque(request):
    termo = request.GET.get('q', '').strip()
    adega = get_adega_atual(request)
    produtos = Produto.objects.filter(Q(adega=adega) & (Q(nome__icontains=termo) | Q(codigo_barras__icontains=termo)))[:10]
    dados = [{"nome": p.nome, "estoque": p.estoque_atual} for p in produtos]
    return JsonResponse(dados, safe=False)

@login_required
def relatorios(request):
    movs = Movimentacao.objects.filter(adega=get_adega_atual(request)).order_by("-data")[:100]
    for m in movs:
        m.valor_total_snapshot = m.quantidade * m.produto.preco_venda
    return render(request, "estoque/relatorios.html", {"movimentacoes": movs})

@login_required
def baixar_relatorio(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    data_arquivo = timezone.now().strftime('%d_%m_%Y')
    response['Content-Disposition'] = f'attachment; filename="relatorio_adega_{data_arquivo}.csv"'
    
    writer = csv.writer(response, delimiter=';')
    response.write(u'\ufeff'.encode('utf8')) # Garante acentos no Excel
    
    # Cabeçalho
    writer.writerow(['Data e Hora', 'Produto', 'Tipo', 'Quantidade', 'Preço Unit.', 'Valor Total'])
    
    movimentacoes = Movimentacao.objects.filter(adega=get_adega_atual(request)).order_by("-data")
    
    faturamento_total = Decimal("0.00")
    
    for m in movimentacoes:
        valor_operacao = m.quantidade * m.produto.preco_venda
        
        # Só somamos no faturamento se for uma SAÍDA (venda)
        if m.tipo == 'SAIDA':
            faturamento_total += valor_operacao
            
        writer.writerow([
            m.data.strftime('%d/%m/%Y %H:%M'),
            m.produto.nome,
            m.tipo,
            m.quantidade,
            f"{m.produto.preco_venda:.2f}".replace('.', ','),
            f"{valor_operacao:.2f}".replace('.', ',')
        ])
    
    # LINHA DE FECHAMENTO
    writer.writerow([]) # Linha em branco para separar
    writer.writerow(['', '', '', '', 'FATURAMENTO TOTAL:', f"R$ {faturamento_total:.2f}".replace('.', ',')])
    
    return response


@login_required
def estoque_baixo(request):
    produtos = Produto.objects.filter(adega=get_adega_atual(request), estoque_atual__lte=5)
    return render(request, "estoque/estoque_baixo.html", {"produtos": produtos})

@login_required
def vendas_hoje(request):
    vendas = Movimentacao.objects.filter(adega=get_adega_atual(request), tipo="SAIDA", data__date=timezone.now().date())
    total = sum(v.quantidade * v.produto.preco_venda for v in vendas)
    return render(request, "estoque/vendas_hoje.html", {"vendas": vendas, "total_valor": total})

@login_required
def limpar_relatorio(request):
    Movimentacao.objects.filter(adega=get_adega_atual(request)).delete()
    return redirect("relatorios")

@csrf_exempt
def admin_gate_check(request):
    if request.method == "POST" and request.POST.get("senha") == settings.ADMIN_GATE_PASSWORD:
        request.session["admin_gate_ok"] = True
        return JsonResponse({"ok": True})
    return JsonResponse({"ok": False}, status=401)

def home(request):
    return redirect("entrada_codigo")

@login_required
def vendas_periodo(request):
    return redirect("vendas_hoje")