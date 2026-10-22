from django.conf import settings
from django.db import models

class Etapa(models.Model):
    nome = models.CharField(max_length=50)
    ordem = models.PositiveIntegerField(default=1)


# Create your models here.
class Ficha(models.Model):
    cliente = models.CharField(max_length=150)
    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
    )
    telefone = models.CharField(max_length=15)
    etapa = models.ForeignKey(
        Etapa,
        on_delete=models.PROTECT,
    )
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
    creado_em = models.TimeField(auto_now_add=True)
    atualizado_em = models.TimeField(auto_now=True)
    todas_financeiras = models.BooleanField(default=False)




