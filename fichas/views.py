from decimal import Decimal
import logging
from uuid import uuid4
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from pathlib import Path
from django.http import FileResponse, Http404
from django.views.decorators.http import require_GET
from django.db import transaction
from django.db.models import Prefetch, Q
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from .forms import AnexosForm
from .models import AnexoFicha

from .forms import EtapaForm, FichaForm
from .models import Etapa, EventoFicha, Ficha


def fichas_visiveis(usuario):
    fichas = Ficha.objects.all()
    if not usuario.has_perm("fichas.ver_todas_fichas"):
        fichas = fichas.filter(vendedor=usuario)
    return fichas


def contexto_quadro(request, formulario=None, formulario_etapa=None):
    fichas = fichas_visiveis(request.user).select_related("vendedor").order_by("-id")
    busca = request.GET.get("q", "").strip()[:100]
    if busca:
        filtro = Q(cliente__icontains=busca) | Q(equipamento__icontains=busca)
        if busca.isdecimal() and len(busca) <= 18:
            filtro |= Q(pk=int(busca))
        fichas = fichas.filter(filtro)
    etapas = list(Etapa.objects.order_by("ordem", "id").prefetch_related(
        Prefetch("ficha_set", queryset=fichas, to_attr="fichas_do_quadro")
    ))
    quantidade = 0
    total = Decimal("0.00")
    for etapa in etapas:
        etapa.valor_do_quadro = sum((f.valor for f in etapa.fichas_do_quadro), Decimal("0.00"))
        quantidade += len(etapa.fichas_do_quadro)
        total += etapa.valor_do_quadro
    return {
        "titulo": "Acompanhamento de fichas", "etapas": etapas,
        # Não usar `formulario or FichaForm()`: um formulário vazio tem avaliação própria.
        "formulario": formulario if formulario is not None else FichaForm(),
        "formulario_etapa": formulario_etapa if formulario_etapa is not None else EtapaForm(),
        "busca": busca, "quantidade": quantidade, "valor_total": total,
        "pode_ver_todas": request.user.has_perm("fichas.ver_todas_fichas"),
    }


@login_required(login_url="login")
@require_http_methods(["GET", "POST"])
def index(request):
    formulario = FichaForm(request.POST) if request.method == "POST" else FichaForm()
    if request.method == "POST":
        if not request.user.has_perm("fichas.add_ficha"):
            raise PermissionDenied
        if formulario.is_valid():
            with transaction.atomic():
                etapa = Etapa.objects.select_for_update().order_by("ordem", "id").first()
                if etapa is None:
                    formulario.add_error(None, "Cadastre uma etapa antes de criar a primeira ficha.")
                else:
                    ficha = formulario.save(commit=False)
                    ficha.vendedor = request.user
                    ficha.etapa = etapa
                    ficha.save()
                    EventoFicha.objects.create(
                        ficha=ficha, autor=request.user, acao=EventoFicha.Acao.CRIACAO,
                        etapa_nova=etapa.nome,
                    )
                    messages.success(request, f"Ficha #{ficha.pk} criada com sucesso.")
                    return redirect("fichas_index")
    return render(request, "fichas/index.html", contexto_quadro(request, formulario=formulario))


@login_required(login_url="login")
@require_http_methods(["GET"])
def ficha_detalhe(request, ficha_id):
    ficha = get_object_or_404(
        fichas_visiveis(request.user).select_related("vendedor", "etapa"), pk=ficha_id,
    )
    campos = []
    corporativos = {"cnpj", "razao_social", "data_abertura"}
    for nome in FichaForm.Meta.fields:
        if nome in corporativos and not ficha.usar_cnpj:
            continue
        campo = Ficha._meta.get_field(nome)
        valor = getattr(ficha, nome)
        if isinstance(valor, bool):
            valor = "Sim" if valor else "Não"
        elif hasattr(valor, "strftime"):
            valor = valor.strftime("%d/%m/%Y")
        elif nome == "valor":
            valor = f"R$ {valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        campos.append((FichaForm.Meta.labels.get(nome, campo.verbose_name), valor))
    return render(request, "fichas/ficha_detalhe.html", {
        "titulo": f"Ficha #{ficha.pk}", "ficha": ficha, "campos": campos,
        "etapas": Etapa.objects.order_by("ordem", "id"),
        "eventos": ficha.eventos.select_related("autor")[:100],
        "anexos": ficha.anexos.select_related("enviado_por"),

    })


@login_required(login_url="login")
@permission_required("fichas.change_ficha", raise_exception=True)
@require_http_methods(["GET", "POST"])
def ficha_editar(request, ficha_id):
    if request.method == "POST":
        with transaction.atomic():
            ficha = get_object_or_404(fichas_visiveis(request.user).select_for_update(), pk=ficha_id)
            anteriores = {nome: getattr(ficha, nome) for nome in FichaForm.Meta.fields}
            formulario = FichaForm(request.POST, instance=ficha)
            if formulario.is_valid():
                alteracoes = {
                    nome: {
                        "rotulo": FichaForm.Meta.labels.get(nome, Ficha._meta.get_field(nome).verbose_name),
                        "antes": anteriores[nome] if anteriores[nome] is None else str(anteriores[nome]),
                        "depois": formulario.cleaned_data[nome] if formulario.cleaned_data[nome] is None else str(formulario.cleaned_data[nome]),
                    }
                    for nome in FichaForm.Meta.fields
                    if anteriores[nome] != formulario.cleaned_data[nome]
                }
                if alteracoes:
                    formulario.save()
                    EventoFicha.objects.create(
                        ficha=ficha, autor=request.user, acao=EventoFicha.Acao.EDICAO,
                        alteracoes=alteracoes,
                    )
                messages.success(request, "Ficha atualizada.")
                return redirect("ficha_detalhe", ficha_id=ficha.pk)
    else:
        ficha = get_object_or_404(fichas_visiveis(request.user), pk=ficha_id)
        formulario = FichaForm(instance=ficha)
    return render(request, "fichas/ficha_form.html", {
        "titulo": f"Editar ficha #{ficha.pk}", "formulario": formulario, "ficha": ficha,
    })


@login_required(login_url="login")
@permission_required("fichas.mover_ficha", raise_exception=True)
@require_POST
def ficha_mover(request, ficha_id):
    json_resposta = request.headers.get("Accept") == "application/json"

    def responder(erro=None, status=200):
        if json_resposta:
            return JsonResponse({"ok": erro is None, "erro": erro}, status=status)
        if erro:
            messages.error(request, erro)
        else:
            messages.success(request, "Ficha movimentada.")
        return redirect("ficha_detalhe", ficha_id=ficha_id)

    try:
        destino_id = int(request.POST.get("etapa", ""))
        origem_id = int(request.POST.get("etapa_origem", ""))
        if not 0 < destino_id < 2**63 or not 0 < origem_id < 2**63:
            raise ValueError
    except (ValueError, TypeError):
        return responder("Selecione uma etapa válida.", 400)

    with transaction.atomic():
        ficha = get_object_or_404(fichas_visiveis(request.user).select_for_update(), pk=ficha_id)
        if ficha.etapa_id != origem_id:
            return responder("Esta ficha já foi movimentada. Atualize a página e tente novamente.", 409)
        # Também trava a etapa de destino para ela não ser excluída durante a operação.
        destino = Etapa.objects.select_for_update().filter(pk=destino_id).first()
        if destino is None:
            return responder("A etapa de destino não existe mais. Atualize a página.", 400)
        if destino.pk == ficha.etapa_id:
            return responder()
        nome_anterior = ficha.etapa.nome
        ficha.etapa = destino
        ficha.save(update_fields=["etapa", "atualizado_em"])
        EventoFicha.objects.create(
            ficha=ficha, autor=request.user, acao=EventoFicha.Acao.MOVIMENTACAO,
            etapa_anterior=nome_anterior, etapa_nova=destino.nome,
        )
    return responder()


@login_required(login_url="login")
@permission_required("fichas.add_etapa", raise_exception=True)
@require_POST
def criar_etapa(request):
    formulario = EtapaForm(request.POST)
    if formulario.is_valid():
        formulario.save()
        messages.success(request, "Etapa cadastrada.")
        return redirect("fichas_index")
    return render(request, "fichas/index.html", contexto_quadro(request, formulario_etapa=formulario))


@login_required(login_url="login")
@permission_required("fichas.change_etapa", raise_exception=True)
@require_http_methods(["GET", "POST"])
def etapa_editar(request, etapa_id):
    etapa = get_object_or_404(Etapa, pk=etapa_id)
    formulario = EtapaForm(request.POST if request.method == "POST" else None, instance=etapa)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(request, "Etapa atualizada.")
        return redirect("fichas_index")
    return render(request, "fichas/etapa_form.html", {
        "titulo": "Editar etapa", "formulario_etapa": formulario, "etapa": etapa,
    })


@login_required(login_url="login")
@permission_required("fichas.delete_etapa", raise_exception=True)
@require_http_methods(["GET", "POST"])
def etapa_excluir(request, etapa_id):
    etapa = get_object_or_404(Etapa, pk=etapa_id)
    if request.method == "POST":
        try:
            with transaction.atomic():
                etapa = get_object_or_404(Etapa.objects.select_for_update(), pk=etapa_id)
                etapa.delete()
        except ProtectedError:
            messages.error(request, "Esta etapa contém fichas. Mova todas para outra etapa antes de excluir.")
        else:
            messages.success(request, "Etapa excluída.")
        return redirect("fichas_index")
    return render(request, "fichas/etapa_excluir.html", {
        "titulo": "Excluir etapa", "etapa": etapa,
    })


@login_required(login_url="login")
@permission_required("fichas.change_ficha", raise_exception=True)
@require_http_methods(["GET", "POST"])
def ficha_anexar(request, ficha_id):
    ficha = get_object_or_404(
        fichas_visiveis(request.user),
        pk=ficha_id,
    )

    formulario = (
        AnexosForm(request.POST, request.FILES)
        if request.method == "POST"
        else AnexosForm()
    )

    if request.method == "POST" and formulario.is_valid():
        arquivos_salvos = []

        try:
            with transaction.atomic():
                for arquivo in formulario.cleaned_data["arquivos"]:
                    anexo = AnexoFicha(
                        ficha=ficha,
                        nome_original=arquivo.name,
                        enviado_por=request.user,
                    )

                    extensao = Path(arquivo.name).suffix.lower()

                    anexo.arquivo.save(
                        f"{uuid4().hex}{extensao}",
                        arquivo,
                        save=False,
                    )
                    arquivos_salvos.append(anexo.arquivo)
                    anexo.save()

        except Exception:
            for salvo in arquivos_salvos:
                try:
                    salvo.storage.delete(salvo.name)
                except Exception:
                    logging.getLogger(__name__).exception(
                        "Não foi possível remover um arquivo após falha no envio."
                    )
            raise

        messages.success(
            request,
            f"{len(arquivos_salvos)} PDF(s) anexado(s) com sucesso.",
        )
        return redirect("ficha_detalhe", ficha_id=ficha.pk)

    return render(request, "fichas/anexos_form.html", {
        "titulo": f"Anexar PDFs à ficha #{ficha.pk}",
        "ficha": ficha,
        "formulario_anexos": formulario,
    })



@login_required(login_url="login")
@require_GET
def anexo_baixar(request, ficha_id, anexo_id):
    ficha = get_object_or_404(
        fichas_visiveis(request.user),
        pk=ficha_id,
    )

    anexo = get_object_or_404(
        AnexoFicha,
        pk=anexo_id,
        ficha=ficha,
    )

    try:
        arquivo = anexo.arquivo.open("rb")
    except FileNotFoundError:
        raise Http404(
            "Arquivo não encontrado no armazenamento."
        ) from None

    resposta = FileResponse(
        arquivo,
        as_attachment=True,
        filename=anexo.nome_original,
    )

    resposta["Cache-Control"] = "private, no-store"

    return resposta