from django import forms
from .models import Contato, Asset, Categoria

class FormServico(forms.ModelForm):
    class Meta:
        model = Asset
        fields = ("nome", "descricao", "preco", "imagem", "arquivo", "ativo", "categoria")
        
class FormContato(forms.ModelForm):
    class Meta:
        model = Contato
        fields = ("nome", "email", "telefone", "mensagem")


class AssetFilterForm(forms.Form):
    busca = forms.CharField(
        label="Nome do asset",
        required=False,
        max_length=100,
        widget=forms.SearchInput(attrs={"placeholder": "Buscar por nome"}),
    )
    categoria = forms.ModelChoiceField(
        label="Categoria",
        queryset=Categoria.objects.none(),
        required=False,
        empty_label="Todas as categorias",
    )
    preco_min = forms.DecimalField(
        label="Preço mínimo (R$)",
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"min": "0", "step": "0.01", "placeholder": "0,00"}),
    )
    preco_max = forms.DecimalField(
        label="Preço máximo (R$)",
        required=False,
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"min": "0", "step": "0.01", "placeholder": "0,00"}),
    )
    status = forms.ChoiceField(
        label="Status",
        required=False,
        choices=(("", "Todos"), ("ativo", "Ativos"), ("inativo", "Inativos")),
    )
    ordem = forms.ChoiceField(
        label="Ordenar por",
        required=False,
        choices=(
            ("", "Padrão"),
            ("menor", "Menor preço"),
            ("maior", "Maior preço"),
            ("nome", "Nome (A–Z)"),
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = Categoria.objects.order_by("nome")

    def clean(self):
        cleaned_data = super().clean()
        preco_min = cleaned_data.get("preco_min")
        preco_max = cleaned_data.get("preco_max")
        if preco_min is not None and preco_max is not None and preco_min > preco_max:
            self.add_error("preco_min", "O preço mínimo não pode ser maior que o preço máximo.")
        return cleaned_data