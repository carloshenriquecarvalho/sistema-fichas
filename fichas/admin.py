from django.contrib import admin

from .models import Etapa


@admin.register(Etapa)
class EtapaAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "ordem")
    ordering = ("ordem", "id")

# As fichas são alteradas pelas views para manter o registro de autor no histórico.
