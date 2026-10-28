"""Dados fictícios apenas para a verificação visual local deste pacote."""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "verificacao.settings")
import django
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from fichas.models import Etapa, EventoFicha, Ficha

call_command("configurar_grupos")
usuario, _ = get_user_model().objects.get_or_create(username="demo.credito")
usuario.set_password("demo-local-apenas")
usuario.save()
usuario.groups.add(Group.objects.get(name="Crédito"))
vendedor, _ = get_user_model().objects.get_or_create(username="Mariana Alves")
etapas = []
for nome, ordem in (("Recebidas", 1), ("Em análise", 2), ("Aprovadas", 3), ("Concluídas", 4)):
    etapa, _ = Etapa.objects.get_or_create(nome=nome, defaults={"ordem": ordem})
    etapas.append(etapa)
nomes = [
    ("Clínica Belle Vie", "Plataforma de ultrassom", "34500", 0),
    ("Camila Rodrigues", "Laser de diodo", "48000", 0),
    ("Studio Essência", "Radiofrequência", "18900", 0),
    ("Fernanda Oliveira", "Criolipólise", "29700", 1),
    ("Clínica Renove", "Plataforma multifuncional", "56000", 1),
    ("Gabriela Martins", "Ultrassom microfocado", "32000", 2),
]
for nome, equipamento, valor, coluna in nomes:
    ficha, criada = Ficha.objects.get_or_create(cliente=nome, defaults={
        "vendedor": vendedor, "etapa": etapas[coluna], "valor": valor, "equipamento": equipamento,
        "telefone": "61999999999", "cpf": "00000000000", "data_nascimento": "1990-01-01",
        "email": "demo@example.com", "endereco": "Endereço fictício", "nome_mae": "Nome fictício",
        "endereco_clinica": "Endereço de teste",
    })
    if criada:
        EventoFicha.objects.create(ficha=ficha, autor=vendedor, acao="criacao", etapa_nova=etapas[coluna].nome)
