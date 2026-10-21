from django.shortcuts import render
from django.http import HttpResponse
# Create your views here.

def index(request):
    return render(request, "fichas/index.html", {
        "titulo": "Meu primeiro app em Django!",
        "fichas": [
            {"id": 1, "nome": "Maria Clara", "valor": 100.00},
            {"id": 2, "nome": "Julia", "valor": 89.00},
            {"id": 3, "nome": "Pereira", "valor": 124.00},
            {"id": 4, "nome": "Marcos", "valor": 653.00},
            {"id": 5, "nome": "Fernando", "valor": 1983.00},
            {"id": 6, "nome": "Pedro", "valor": 1823.00},
        ]
    })