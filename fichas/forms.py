from django import forms
from pathlib import Path
from django.core.validators import FileExtensionValidator

from .models import Etapa, Ficha


class FichaForm(forms.ModelForm):
    class Meta:
        model = Ficha
        # Vendedor e etapa são definidos no servidor, nunca pelo formulário de cadastro.
        fields = [
            "cliente", "telefone", "email", "cpf", "data_nascimento",
            "nome_mae", "endereco", "rede_social", "equipamento", "valor",
            "endereco_clinica", "todas_financeiras", "usar_cnpj", "cnpj",
            "razao_social", "data_abertura",
        ]
        labels = {
            "cliente": "Nome do cliente", "telefone": "Telefone", "email": "E-mail",
            "cpf": "CPF", "data_nascimento": "Data de nascimento", "nome_mae": "Nome da mãe",
            "endereco": "Endereço do cliente", "rede_social": "Rede social (opcional)",
            "equipamento": "Equipamento", "valor": "Valor solicitado (R$)",
            "endereco_clinica": "Endereço da clínica", "todas_financeiras": "Consultar todas as financeiras",
            "cnpj": "CNPJ", "razao_social": "Razão social", "data_abertura": "Data de abertura",
        }
        widgets = {
            "data_nascimento": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "data_abertura": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "endereco": forms.Textarea(attrs={"rows": 3}),
            "valor": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
            "telefone": forms.TextInput(attrs={"type": "tel"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rede_social"].required = False
        ativo = self.fields["usar_cnpj"].to_python(self["usar_cnpj"].value())
        for nome in ("cnpj", "razao_social", "data_abertura"):
            self.fields[nome].required = ativo
            self.fields[nome].disabled = not ativo
        self.fields["cnpj"].help_text = "Informe somente os números."

    def clean_valor(self):
        valor = self.cleaned_data["valor"]
        if valor <= 0:
            raise forms.ValidationError("Informe um valor maior que zero.")
        return valor

    def clean(self):
        dados = super().clean()
        if not dados.get("usar_cnpj"):
            dados.update(cnpj="", razao_social="", data_abertura=None)
        return dados


class EtapaForm(forms.ModelForm):
    class Meta:
        model = Etapa
        fields = ["nome", "ordem"]
        labels = {"nome": "Nome da etapa", "ordem": "Posição no Kanban"}

    def clean_nome(self):
        nome = self.cleaned_data["nome"].strip()
        if not nome:
            raise forms.ValidationError("Informe o nome da etapa.")
        return nome


class MultiplosAnexosInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiplosAnexosField(forms.FileField):
    widget = MultiplosAnexosInput

    MAX_ARQUIVOS = 6
    MAX_BYTES = 10 * 1024 * 1024

    def clean(self, data, initial=None):
        if not data:
            raise forms.ValidationError(
                "Selecione pelo menos um arquivo."
            )

        arquivos = data if isinstance(data, (list, tuple)) else [data]

        if len(arquivos) > self.MAX_ARQUIVOS:
            raise forms.ValidationError(
                "Envie no máximo 6 arquivos por vez."
            )

        validados = []

        for enviado in arquivos:
            arquivo = super().clean(enviado, initial)

            if arquivo.size > self.MAX_BYTES:
                raise forms.ValidationError(
                    "Cada arquivo deve ter no máximo 10 MiB."
                )

            extensao = Path(arquivo.name).suffix.lower()
            arquivo.seek(0)

            if extensao == ".pdf":
                assinatura = arquivo.read(5)
                arquivo.seek(0)

                if assinatura != b"%PDF-":
                    raise forms.ValidationError(
                        "Um dos arquivos não tem o cabeçalho esperado de um PDF."
                    )
            else:
                arquivo = forms.ImageField().clean(arquivo)

                formato_esperado = (
                    "PNG" if extensao == ".png" else "JPEG"
                )

                if arquivo.image.format != formato_esperado:
                    raise forms.ValidationError(
                        "A extensão da imagem não corresponde ao conteúdo."
                    )

            arquivo.seek(0)
            validados.append(arquivo)

        return validados


class AnexosForm(forms.Form):
    arquivos = MultiplosAnexosField(
        label="Selecionar documentos",
        max_length=255,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "png", "jpg", "jpeg"],
            ),
        ],
        widget=MultiplosAnexosInput(
            attrs={"accept": ".pdf,.png,.jpg,.jpeg"},
        ),
        help_text=(
            "PDF, PNG ou JPG. Até 6 arquivos por envio, "
            "com até 10 MiB cada."
        ),
    )