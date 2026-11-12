from decimal import Decimal
from uuid import uuid4

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models


def generate_product_sku():
    return f'GBF-{uuid4().hex.upper()}'


class PhysicalCardPrice(models.Model):
    """Preço único do item fixo do caixa, separado dos produtos do cardápio."""
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    preco = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('2.00'),
        validators=[MinValueValidator(Decimal('0.01'))], verbose_name='Preço',
    )

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(id=1), name='physical_card_price_singleton'),
            models.CheckConstraint(condition=models.Q(preco__gte=Decimal('0.01')), name='physical_card_price_positive'),
        ]

    @classmethod
    def current(cls):
        price, _ = cls.objects.get_or_create(pk=1)
        return price.preco


class Category(models.Model):
    nome = models.CharField(max_length=100, verbose_name='Nome')

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Product(models.Model):
    nome = models.CharField(max_length=200, verbose_name='Nome')
    sku = models.CharField(
        max_length=36, unique=True, default=generate_product_sku,
        editable=False, verbose_name='SKU',
    )
    ncm = models.CharField(
        max_length=8, blank=True, default='', verbose_name='NCM',
        validators=[RegexValidator(r'\A[0-9]{8}\Z', 'Informe um NCM com exatamente 8 dígitos.')],
    )
    descricao = models.TextField(blank=True, verbose_name='Descrição', max_length=500)
    preco = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Preço')
    categoria = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='produtos',
        verbose_name='Categoria'
    )
    imagem = models.ImageField(upload_to='produtos/', blank=True, null=True, verbose_name='Imagem')
    imagem_base64 = models.TextField(blank=True, null=True, verbose_name='Imagem (Base64)')
    disponivel = models.BooleanField(default=True, verbose_name='Disponível')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['categoria', 'nome']

    def __str__(self):
        return f'{self.nome} - R$ {self.preco}'
