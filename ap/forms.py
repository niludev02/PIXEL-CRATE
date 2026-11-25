from django import forms
from .models import Contato, Asset

class FormServico(forms.ModelForm):
    class Meta:
        model = Asset
        fields = ("nome", "descricao", "preco", "imagem", "arquivo", "ativo", "categoria")
        
class FormContato(forms.ModelForm):
    class Meta:
        model = Contato
        fields = ("nome", "email", "telefone", "mensagem")