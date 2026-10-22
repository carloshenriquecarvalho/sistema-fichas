from django.contrib import admin
from .models import Etapa


class EtapaAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "ordem")
    ordering = ("ordem", "id")


admin.site.register(Etapa, EtapaAdmin)