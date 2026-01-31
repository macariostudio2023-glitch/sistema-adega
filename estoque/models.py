from django.db import models


# =========================
# ADEGA (empresa / cliente)
# =========================
class Adega(models.Model):
    nome = models.CharField(max_length=150)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Adega"
        verbose_name_plural = "Adegas"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


# =========================
# CATEGORIA
# =========================
class Categoria(models.Model):
    nome = models.CharField(max_length=100)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


# =========================
# PRODUTO (por adega)
# =========================
class Produto(models.Model):
    adega = models.ForeignKey(
        Adega,
        on_delete=models.CASCADE,
        related_name="produtos"
    )

    nome = models.CharField(max_length=150)

    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="produtos"
    )

    # 🔹 Código de barras (pode repetir em OUTRA adega)
    codigo_barras = models.CharField(
        max_length=60,
        blank=True,
        null=True
    )

    preco_custo = models.DecimalField(max_digits=10, decimal_places=2)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2)
    estoque_atual = models.IntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ["nome"]

        # 🔒 Impede duplicar código DENTRO da mesma adega
        constraints = [
            models.UniqueConstraint(
                fields=["adega", "codigo_barras"],
                name="unique_codigo_por_adega"
            )
        ]

    def __str__(self):
        return f"{self.nome} ({self.adega.nome})"


# =========================
# MOVIMENTAÇÃO DE ESTOQUE
# =========================
class Movimentacao(models.Model):
    TIPO_CHOICES = (
        ("ENTRADA", "Entrada"),
        ("SAIDA", "Saída"),
    )

    adega = models.ForeignKey(
        Adega,
        on_delete=models.CASCADE,
        related_name="movimentacoes"
    )

    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name="movimentacoes"
    )

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    quantidade = models.PositiveIntegerField()
    observacao = models.TextField(blank=True, null=True)
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"
        ordering = ["-data"]

    def save(self, *args, **kwargs):
        # 🔥 Regra de negócio do estoque
        if not self.pk:
            if self.tipo == "ENTRADA":
                self.produto.estoque_atual += self.quantidade
            elif self.tipo == "SAIDA":
                self.produto.estoque_atual -= self.quantidade

            self.produto.save()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tipo} - {self.produto.nome} ({self.adega.nome})"



