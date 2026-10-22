from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import render, redirect

from .models import Etapa
from .forms import FichaForm, EtapaForm

# Create your views here.

def index(request):
    if request.method == "POST":
        if not request.user.is_authenticated:
            return HttpResponse(
                "Faça login antes de criar uma ficha.",
                status=403,
            )

        formulario = FichaForm(request.POST)

        if formulario.is_valid():
            etapa_inicial = Etapa.objects.order_by("ordem", "id").first()

            if etapa_inicial is None:
                formulario.add_error(
                    None,
                    "É necessário cadastrar uma etapa antes de criar fichas.",
                )
            else:
                ficha = formulario.save(commit=False)
                ficha.vendedor = request.user
                ficha.etapa = etapa_inicial
                ficha.save()

                return redirect("fichas_index")
    else:
        formulario = FichaForm()

    formulario_etapa = EtapaForm()

    etapas = Etapa.objects.order_by("ordem", "id")

    contexto = {
        "titulo": "Fichas cadastradas",
        "etapas": etapas,
        "formulario": formulario,
        "formulario_etapa": formulario_etapa,
    }


    return render(request, "fichas/index.html", contexto)


def criar_etapa(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    if not request.user.has_perm("fichas.add_etapa"):
        return HttpResponse(
            "Você não tem permissão para criar etapas.",
            status=403,
        )

    formulario_etapa = EtapaForm(request.POST)

    if formulario_etapa.is_valid():
        formulario_etapa.save()
        return redirect("fichas_index")

    contexto = {
        "titulo": "Fichas cadastradas",
        "etapas": Etapa.objects.order_by("ordem", "id"),
        "formulario": FichaForm(),
        "formulario_etapa": formulario_etapa,
    }

    return render(request, "fichas/index.html", contexto)