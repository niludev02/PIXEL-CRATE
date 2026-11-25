from django.contrib import admin
from .models import Asset, Categoria, Contato, ItemPedido, Pedido


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome", "descricao")
    ordering = ("nome",)
    list_per_page = 25


@admin.register(Contato)
class ContatoAdmin(admin.ModelAdmin):
    list_display = ("nome", "email", "telefone")
    search_fields = ("nome", "email", "telefone", "mensagem")
    ordering = ("nome",)
    readonly_fields = ("nome", "email", "telefone", "mensagem")
    list_per_page = 25


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "preco", "ativo", "criado_em")
    list_filter = ("categoria", "ativo")
    search_fields = ("nome", "descricao", "categoria__nome")
    ordering = ("nome", "preco")
    date_hierarchy = "criado_em"
    readonly_fields = ("criado_em", "atualizado_em")
    list_per_page = 25


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ("preco_unitario",)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "status", "criado_em")
    list_filter = ("status", "criado_em")
    search_fields = ("usuario__username", "usuario__email")
    inlines = (ItemPedidoInline,)


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "asset", "preco_unitario")
    search_fields = ("pedido__usuario__username", "asset__nome")
