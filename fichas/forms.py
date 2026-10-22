from django import forms
from .models import Ficha
from .models import Etapa

class FichaForm(forms.ModelForm):
    class Meta:
        model = Ficha
        fields = [
            "cliente",
            "telefone",
            "valor",
            "cpf",
            "data_nascimento",
            "email",
            "equipamento",
            "endereco",
            "rede_social",
            "nome_mae",
            "endereco_clinica",
            "usar_cnpj",
            "cnpj",
            "razao_social",
            "data_abertura",
            "todas_financeiras",
        ]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        ativo = bool(self["usar_cnpj"].value())

        for nome in ("cnpj", "razao_social", "data_abertura"):
            self.fields[nome].required = ativo
            self.fields[nome].disabled = not ativo

class EtapaForm(forms.ModelForm):
    class Meta:
        model = Etapa
        fields = [
            "nome",
            "ordem",
        ]