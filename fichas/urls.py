from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


urlpatterns = [
    path("", views.index, name="fichas_index"),
    path("entrar/", auth_views.LoginView.as_view(
        template_name="registration/login.html", next_page="fichas_index",
    ), name="login"),
    path("sair/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    path("etapas/criar/", views.criar_etapa, name="etapa_criar"),
    path("etapas/<int:etapa_id>/editar/", views.etapa_editar, name="etapa_editar"),
    path("etapas/<int:etapa_id>/excluir/", views.etapa_excluir, name="etapa_excluir"),
    path("<int:ficha_id>/", views.ficha_detalhe, name="ficha_detalhe"),
    path("<int:ficha_id>/editar/", views.ficha_editar, name="ficha_editar"),
    path("<int:ficha_id>/mover/", views.ficha_mover, name="ficha_mover"),
    path(
        "<int:ficha_id>/anexos/",
        views.ficha_anexar,
        name="ficha_anexar",
    ),
    path(
        "<int:ficha_id>/anexos/<int:anexo_id>/baixar/",
        views.anexo_baixar,
        name="anexo_baixar",
    ),
]
