from django.contrib.auth.models import User
from django.db import models

# Create your models here.

class Categoria(models.Model):
    nome = models.CharField(max_length=100)  
    descricao = models.TextField(blank=True)  
    ativo = models.BooleanField(default=True)
    def __str__(self):
        return self.nome

class Asset(models.Model):
    nome = models.CharField("Nome do asset", max_length=100)
    descricao = models.TextField("Descrição", blank=True)
    preco = models.DecimalField("Preço", max_digits=10, decimal_places=2)
    imagem = models.ImageField("Imagem de prévia", upload_to='servicos/', blank=True, null=True)
    arquivo = models.FileField("Arquivo para download", upload_to='assets/', blank=True, null=True)
    ativo = models.BooleanField("Ativo (aparece na vitrine)", default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    categoria = models.ForeignKey(
        Categoria,
        verbose_name="Categoria",
        on_delete=models.PROTECT,
        related_name='assets',
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Asset"
        verbose_name_plural = "Assets"

    def __str__(self):
        return self.nome


class Pedido(models.Model):
    STATUS_PENDENTE = "pendente"
    STATUS_PAGO = "pago"
    STATUS_CANCELADO = "cancelado"
    STATUS_CHOICES = [
        (STATUS_PENDENTE, "Pendente"),
        (STATUS_PAGO, "Pago"),
        (STATUS_CANCELADO, "Cancelado"),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pedidos")
    criado_em = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PAGO)
    oculto = models.BooleanField("Removido da lista do usuário", default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("usuario",),
                condition=models.Q(status="pendente"),
                name="unique_pending_pedido_per_user",
            )
        ]

    def total(self):
        return sum((item.preco_unitario for item in self.itens.all()), start=0)

    def __str__(self):
        return f"Pedido #{self.pk} - {self.usuario}"


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="itens")
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="itens_pedido")
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ("pedido", "asset")

    def __str__(self):
        return f"{self.asset.nome} ({self.pedido_id})"
    
class Contato(models.Model):
    nome = models.CharField(max_length=100)
    email = models.EmailField()
    telefone = models.CharField(max_length=20, blank=True)
    mensagem = models.TextField() 
    
    def __str__(self):
        return self.nome


# Compatibilidade temporaria para codigo antigo que ainda importe Servico.
Servico = Asset