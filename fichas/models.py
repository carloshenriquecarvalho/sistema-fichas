from django.core.validators import FileExtensionValidator
from django.conf import settings
from django.db import models

class Etapa(models.Model):
    nome = models.CharField(max_length=50)
    ordem = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.nome


class Ficha(models.Model):
    cliente = models.CharField(max_length=150)
    vendedor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    telefone = models.CharField(max_length=15)
    etapa = models.ForeignKey(Etapa, on_delete=models.PROTECT)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    cpf = models.CharField(max_length=15)
    data_nascimento = models.DateField()
    email = models.EmailField()
    usar_cnpj = models.BooleanField(default=False, verbose_name="Usar CNPJ")
    equipamento = models.CharField(max_length=50)
    endereco = models.TextField()
    rede_social = models.CharField(max_length=150, default="")
    nome_mae = models.CharField(max_length=150)
    endereco_clinica = models.CharField(max_length=150)
    cnpj = models.CharField(max_length=15, blank=True)
    razao_social = models.CharField(max_length=150, blank=True)
    data_abertura = models.DateField(blank=True, null=True)
    # Campos existentes preservados para não converter horários antigos em datas inventadas.
    creado_em = models.TimeField(auto_now_add=True)
    atualizado_em = models.TimeField(auto_now=True)
    todas_financeiras = models.BooleanField(default=False)

    class Meta:
        permissions = [
            ("ver_todas_fichas", "Pode visualizar fichas de todos os vendedores"),
            ("mover_ficha", "Pode movimentar fichas entre etapas"),
        ]

    def __str__(self):
        return f"#{self.pk} · {self.cliente}"


class EventoFicha(models.Model):
    class Acao(models.TextChoices):
        CRIACAO = "criacao", "Ficha criada"
        EDICAO = "edicao", "Dados atualizados"
        MOVIMENTACAO = "movimentacao", "Etapa alterada"

    ficha = models.ForeignKey(Ficha, on_delete=models.PROTECT, related_name="eventos")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    acao = models.CharField(max_length=20, choices=Acao.choices)
    etapa_anterior = models.CharField(max_length=50, blank=True)
    etapa_nova = models.CharField(max_length=50, blank=True)
    alteracoes = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em", "-id"]

    def __str__(self):
        return f"{self.get_acao_display()} · ficha #{self.ficha_id}"


class AnexoFicha(models.Model):
    ficha = models.ForeignKey(
        Ficha,
        on_delete=models.PROTECT,
        related_name="anexos",
    )

    arquivo = models.FileField(
        upload_to="fichas/anexos/",
        max_length=255,
        validators=[
            FileExtensionValidator(allowed_extensions=["pdf", "png", "jpg", "jpeg"],
            ),
        ],
    )

    nome_original = models.CharField(max_length=255)

    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
    )

    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-enviado_em", "-id"]

    def __str__(self):
        return self.nome_original

class RegistroExclusaoFicha(models.Model):
    ficha_id_original = models.PositiveBigIntegerField()

    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="exclusoes_de_fichas",
    )

    excluida_em = models.DateTimeField(auto_now_add=True)