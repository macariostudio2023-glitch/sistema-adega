from datetime import timedelta

from django import forms
from django.utils import timezone

from .models import Categoria


class EntradaCodigoBarrasForm(forms.Form):
    codigo_barras = forms.CharField(
        label="Código de barras",
        max_length=60,
        widget=forms.TextInput(attrs={
            "autofocus": True,
            "placeholder": "Passe o leitor aqui e aperte ENTER"
        })
    )
    quantidade = forms.IntegerField(
        label="Quantidade",
        min_value=1,
        initial=1
    )


class SaidaCodigoBarrasForm(forms.Form):
    codigo_barras = forms.CharField(
        label="Código de barras",
        max_length=60,
        widget=forms.TextInput(attrs={
            "autofocus": True,
            "placeholder": "Passe o leitor aqui"
        })
    )
    quantidade = forms.IntegerField(
        label="Quantidade",
        min_value=1,
        initial=1
    )


class NovoProdutoPorCodigoForm(forms.Form):
    codigo_barras = forms.CharField(
        label="Código de barras",
        max_length=60,
        widget=forms.TextInput(attrs={
            "readonly": True
        })
    )
    nome = forms.CharField(
        label="Nome do produto",
        max_length=150
    )
    categoria = forms.ModelChoiceField(
        label="Categoria",
        queryset=Categoria.objects.all()
    )
    preco_custo = forms.DecimalField(
        label="Preço de custo",
        max_digits=10,
        decimal_places=2
    )
    preco_venda = forms.DecimalField(
        label="Preço de venda",
        max_digits=10,
        decimal_places=2
    )
    estoque_inicial = forms.IntegerField(
        label="Estoque inicial",
        min_value=0,
        initial=0
    )


class FiltroEstoqueBaixoForm(forms.Form):
    limite = forms.IntegerField(
        label="Estoque baixo (até)",
        min_value=0,
        initial=5
    )


class FiltroPeriodoVendasForm(forms.Form):
    data_inicio = forms.DateField(
        label="Data inicial",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"})
    )
    data_fim = forms.DateField(
        label="Data final",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ Se o usuário não informou datas, preenche automático:
        # últimos 7 dias até hoje
        if not self.data.get("data_inicio") and not self.data.get("data_fim"):
            hoje = timezone.localdate()
            self.initial["data_inicio"] = hoje - timedelta(days=7)
            self.initial["data_fim"] = hoje
