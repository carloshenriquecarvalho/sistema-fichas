from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from .forms import FichaForm
from .models import Etapa, EventoFicha, Ficha


class FluxoFichasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("configurar_grupos", stdout=StringIO())
        Usuario = get_user_model()
        cls.vendedor = Usuario.objects.create_user(username="vendedor", password="teste-local-123")
        cls.outro = Usuario.objects.create_user(username="outro", password="teste-local-123")
        cls.credito = Usuario.objects.create_user(username="credito", password="teste-local-123")
        for usuario in (cls.vendedor, cls.outro):
            usuario.groups.add(Group.objects.get(name="Vendedores"))
        cls.credito.groups.add(Group.objects.get(name="Crédito"))
        cls.inicial = Etapa.objects.create(id=7, nome="Recebidas", ordem=1)
        cls.analise = Etapa.objects.create(id=12, nome="Em análise", ordem=2)
        cls.ficha = Ficha.objects.create(
            **cls.dados_modelo("Cliente da equipe"), vendedor=cls.outro, etapa=cls.inicial,
        )
        cls.propria = Ficha.objects.create(
            **cls.dados_modelo("Cliente pessoal"), vendedor=cls.vendedor, etapa=cls.inicial,
        )

    @staticmethod
    def dados_modelo(cliente="Cliente novo"):
        return {
            "cliente": cliente, "telefone": "61999999999", "valor": "12000.00",
            "cpf": "00000000000", "data_nascimento": "1990-01-01", "email": "teste@example.com",
            "equipamento": "Equipamento de teste", "endereco": "Rua de teste, 10",
            "nome_mae": "Nome de teste", "endereco_clinica": "Clínica de teste",
        }

    def setUp(self):
        self.client.force_login(self.vendedor)

    def test_visitante_precisa_login(self):
        self.client.logout()
        self.assertRedirects(self.client.get(reverse("fichas_index")), "/fichas/entrar/?next=/fichas/")

    def test_login_e_logout_post(self):
        self.client.logout()
        resposta = self.client.post(reverse("login"), {"username": "vendedor", "password": "teste-local-123"})
        self.assertRedirects(resposta, reverse("fichas_index"))
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))

    def test_vendedor_so_ve_proprias_no_quadro_e_busca(self):
        resposta = self.client.get(reverse("fichas_index"))
        self.assertContains(resposta, "Cliente pessoal")
        self.assertNotContains(resposta, "Cliente da equipe")
        resposta = self.client.get(reverse("fichas_index"), {"q": self.ficha.pk})
        self.assertEqual(resposta.context["quantidade"], 0)

    def test_credito_ve_todas(self):
        self.client.force_login(self.credito)
        resposta = self.client.get(reverse("fichas_index"))
        self.assertContains(resposta, "Cliente pessoal")
        self.assertContains(resposta, "Cliente da equipe")

    def test_staff_nao_ganha_acesso_global(self):
        self.vendedor.is_staff = True
        self.vendedor.save()
        self.assertNotContains(self.client.get(reverse("fichas_index")), "Cliente da equipe")

    def test_nao_acessa_nem_edita_id_de_outro_vendedor(self):
        self.assertEqual(self.client.get(reverse("ficha_detalhe", args=[self.ficha.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("ficha_editar", args=[self.ficha.pk]), self.dados_modelo()).status_code, 404)

    def test_criacao_usa_usuario_e_etapa_reais_ignora_falsificacao(self):
        dados = {**self.dados_modelo(), "vendedor": self.outro.pk, "etapa": self.analise.pk}
        resposta = self.client.post(reverse("fichas_index"), dados)
        self.assertRedirects(resposta, reverse("fichas_index"))
        ficha = Ficha.objects.latest("id")
        self.assertEqual(ficha.vendedor, self.vendedor)
        self.assertEqual(ficha.etapa_id, 7)  # Não depende de uma etapa de ID 1.
        self.assertEqual(ficha.eventos.get().autor, self.vendedor)

    def test_criacao_nao_exige_cnpj_quando_desmarcado(self):
        dados = {**self.dados_modelo(), "cnpj": "LIXO", "razao_social": "IGNORAR", "data_abertura": "INVÁLIDA"}
        self.assertRedirects(self.client.post(reverse("fichas_index"), dados), reverse("fichas_index"))
        ficha = Ficha.objects.latest("id")
        self.assertEqual(ficha.cnpj, "")
        self.assertIsNone(ficha.data_abertura)

    def test_cnpj_marcado_exige_tres_campos_no_servidor(self):
        resposta = self.client.post(reverse("fichas_index"), {**self.dados_modelo(), "usar_cnpj": "on"})
        self.assertEqual(resposta.status_code, 200)
        self.assertSetEqual(set(resposta.context["formulario"].errors), {"cnpj", "razao_social", "data_abertura"})
        self.assertContains(resposta, "data-autoopen")

    def test_cnpj_valido_salva_com_data(self):
        dados = {**self.dados_modelo(), "usar_cnpj": "on", "cnpj": "00000000000000", "razao_social": "Empresa teste", "data_abertura": "2020-01-02"}
        self.assertRedirects(self.client.post(reverse("fichas_index"), dados), reverse("fichas_index"))
        self.assertTrue(Ficha.objects.latest("id").usar_cnpj)

    def test_sem_etapas_retorna_erro_no_form_sem_integrity_error(self):
        with patch("fichas.views.Etapa.objects.select_for_update") as consulta:
            consulta.return_value.order_by.return_value.first.return_value = None
            resposta = self.client.post(reverse("fichas_index"), self.dados_modelo())
        self.assertContains(resposta, "Cadastre uma etapa antes")
        self.assertEqual(Ficha.objects.count(), 2)

    def test_erro_de_historico_desfaz_criacao(self):
        with patch("fichas.views.EventoFicha.objects.create", side_effect=RuntimeError("falha simulada")):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse("fichas_index"), self.dados_modelo())
        self.assertEqual(Ficha.objects.count(), 2)

    def test_edicao_registra_autor_e_nao_muda_dono_ou_etapa(self):
        dados = {**self.dados_modelo("Nome corrigido"), "vendedor": self.outro.pk, "etapa": self.analise.pk}
        resposta = self.client.post(reverse("ficha_editar", args=[self.propria.pk]), dados)
        self.assertRedirects(resposta, reverse("ficha_detalhe", args=[self.propria.pk]))
        self.propria.refresh_from_db()
        self.assertEqual(self.propria.cliente, "Nome corrigido")
        self.assertEqual(self.propria.vendedor, self.vendedor)
        self.assertEqual(self.propria.etapa, self.inicial)
        evento = self.propria.eventos.get()
        self.assertEqual(evento.acao, EventoFicha.Acao.EDICAO)
        self.assertEqual(evento.alteracoes["cliente"]["antes"], "Cliente pessoal")

    def test_edicao_desmarcando_cnpj_limpa_dados_corporativos(self):
        self.propria.usar_cnpj = True
        self.propria.cnpj = "00000000000000"
        self.propria.razao_social = "Empresa antiga"
        self.propria.data_abertura = "2020-01-01"
        self.propria.save()
        self.client.post(reverse("ficha_editar", args=[self.propria.pk]), self.dados_modelo())
        self.propria.refresh_from_db()
        self.assertEqual(self.propria.cnpj, "")
        self.assertIsNone(self.propria.data_abertura)

    def test_vendedor_nao_move_nem_cria_etapa(self):
        self.assertEqual(self.client.post(reverse("ficha_mover", args=[self.propria.pk]), {"etapa": self.analise.pk, "etapa_origem": self.inicial.pk}).status_code, 403)
        self.assertEqual(self.client.post(reverse("etapa_criar"), {"nome": "Invasão", "ordem": 3}).status_code, 403)

    def test_credito_move_e_registra_historico(self):
        self.client.force_login(self.credito)
        resposta = self.client.post(reverse("ficha_mover", args=[self.ficha.pk]), {"etapa": self.analise.pk, "etapa_origem": self.inicial.pk}, HTTP_ACCEPT="application/json")
        self.assertEqual(resposta.status_code, 200)
        self.ficha.refresh_from_db()
        self.assertEqual(self.ficha.etapa, self.analise)
        evento = self.ficha.eventos.get()
        self.assertEqual(evento.autor, self.credito)
        self.assertEqual(evento.etapa_anterior, "Recebidas")
        self.assertEqual(evento.etapa_nova, "Em análise")

    def test_rejeita_movimentacao_sobre_etapa_desatualizada(self):
        self.client.force_login(self.credito)
        resposta = self.client.post(reverse("ficha_mover", args=[self.ficha.pk]), {"etapa": self.analise.pk, "etapa_origem": self.analise.pk}, HTTP_ACCEPT="application/json")
        self.assertEqual(resposta.status_code, 409)
        self.assertFalse(self.ficha.eventos.exists())

    def test_etapa_inexistente_nao_altera_ficha(self):
        self.client.force_login(self.credito)
        resposta = self.client.post(reverse("ficha_mover", args=[self.ficha.pk]), {"etapa": 98765, "etapa_origem": self.inicial.pk}, HTTP_ACCEPT="application/json")
        self.assertEqual(resposta.status_code, 400)
        self.ficha.refresh_from_db()
        self.assertEqual(self.ficha.etapa, self.inicial)

    def test_permissao_mover_sozinha_nao_abre_ficha_alheia(self):
        self.vendedor.user_permissions.add(Permission.objects.get(content_type__app_label="fichas", codename="mover_ficha"))
        resposta = self.client.post(reverse("ficha_mover", args=[self.ficha.pk]), {"etapa": self.analise.pk, "etapa_origem": self.inicial.pk})
        self.assertEqual(resposta.status_code, 404)

    def test_crud_etapa_com_protecao_de_etapa_ocupada(self):
        self.client.force_login(self.credito)
        self.assertRedirects(self.client.post(reverse("etapa_criar"), {"nome": "Concluídas", "ordem": 3}), reverse("fichas_index"))
        etapa = Etapa.objects.get(nome="Concluídas")
        self.assertRedirects(self.client.post(reverse("etapa_editar", args=[etapa.pk]), {"nome": "Finalizadas", "ordem": 5}), reverse("fichas_index"))
        self.client.post(reverse("etapa_excluir", args=[self.inicial.pk]))
        self.assertTrue(Etapa.objects.filter(pk=self.inicial.pk).exists())
        self.client.post(reverse("etapa_excluir", args=[etapa.pk]))
        self.assertFalse(Etapa.objects.filter(pk=etapa.pk).exists())

    def test_reordenar_etapa_nao_reassocia_fichas(self):
        self.client.force_login(self.credito)
        self.client.post(reverse("etapa_editar", args=[self.inicial.pk]), {"nome": "Recebidas", "ordem": 50})
        self.ficha.refresh_from_db()
        self.assertEqual(self.ficha.etapa_id, self.inicial.pk)

    def test_get_nao_movimenta_ou_cria_etapa(self):
        self.client.force_login(self.credito)
        self.assertEqual(self.client.get(reverse("ficha_mover", args=[self.ficha.pk])).status_code, 405)
        self.assertEqual(self.client.get(reverse("etapa_criar")).status_code, 405)

    def test_csrf_obrigatorio_para_post(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.credito)
        self.assertEqual(cliente.post(reverse("ficha_mover", args=[self.ficha.pk]), {"etapa": self.analise.pk, "etapa_origem": self.inicial.pk}).status_code, 403)

    def test_html_escapado_no_quadro(self):
        self.propria.cliente = "<script>alert(1)</script>"
        self.propria.save()
        resposta = self.client.get(reverse("fichas_index"))
        self.assertNotContains(resposta, "<script>alert(1)</script>")
        self.assertContains(resposta, "&lt;script&gt;")

    def test_telas_de_edicao_e_datas_existentes(self):
        resposta = self.client.get(reverse("ficha_editar", args=[self.propria.pk]))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'value="1990-01-01"')
        formulario = FichaForm(instance=self.propria)
        self.assertIn("usar_cnpj", formulario.fields)

    def test_comando_grupos_pode_ser_executado_novamente(self):
        call_command("configurar_grupos", stdout=StringIO())
        self.assertEqual(Group.objects.filter(name="Crédito").count(), 1)
