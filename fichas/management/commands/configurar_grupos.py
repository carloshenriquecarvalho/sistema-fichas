from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Cria os grupos Vendedores e Crédito. Não cria usuários nem altera senhas."

    @transaction.atomic
    def handle(self, *args, **options):
        grupos = {
            "Vendedores": {"add_ficha", "view_ficha", "change_ficha", "view_etapa"},
            "Crédito": {
                "add_ficha", "view_ficha", "change_ficha", "ver_todas_fichas", "mover_ficha",
                "add_etapa", "view_etapa", "change_etapa", "delete_etapa",
            },
        }
        for nome, codigos in grupos.items():
            permissoes = Permission.objects.filter(content_type__app_label="fichas", codename__in=codigos)
            encontrados = set(permissoes.values_list("codename", flat=True))
            if encontrados != codigos:
                raise CommandError("Faltam permissões. Execute migrate antes de configurar_grupos.")
            grupo, _ = Group.objects.get_or_create(name=nome)
            # Adiciona as permissões necessárias sem remover concessões anteriores.
            grupo.permissions.add(*permissoes)
            self.stdout.write(self.style.SUCCESS(f"Grupo {nome} configurado."))
