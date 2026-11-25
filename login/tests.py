from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from urllib.parse import urlsplit

from .models import Perfil


class CadastroViewTests(TestCase):
    def test_get_exibe_formulario_sem_mensagem_de_sucesso(self):
        response = self.client.get(reverse("cadastrar_usuario"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "cadastro.html")
        self.assertContains(response, "Cadastrar usuário")
        self.assertNotContains(response, "Usuário cadastrado com sucesso!")

    def test_cadastro_valido_cria_usuario_e_redireciona_para_login(self):
        response = self.client.post(
            reverse("cadastrar_usuario"),
            {
                "username": "novo_usuario",
                "email": "novo@example.com",
                "password1": "UmaSenha-Forte-987!",
                "password2": "UmaSenha-Forte-987!",
            },
            follow=True,
        )

        self.assertEqual(response.redirect_chain, [(reverse("login"), 302)])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Usuário cadastrado com sucesso!")
        usuario = User.objects.get(username="novo_usuario")
        self.assertEqual(usuario.email, "novo@example.com")
        self.assertTrue(Perfil.objects.filter(usuario=usuario, tipo_usuario="cliente").exists())

    def test_cadastro_invalido_mostra_erros_e_nao_cria_usuario(self):
        response = self.client.post(
            reverse("cadastrar_usuario"),
            {
                "username": "usuario_invalido",
                "email": "invalido@example.com",
                "password1": "senha",
                "password2": "diferente",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "cadastro.html")
        self.assertTrue(response.context["form"].errors)
        self.assertContains(response, "Não foi possível concluir o cadastro")
        self.assertContains(
            response,
            str(response.context["form"].errors["password2"][0]),
        )
        self.assertFalse(User.objects.filter(username="usuario_invalido").exists())
        self.assertFalse(Perfil.objects.exists())


class DashboardViewTests(TestCase):
    def test_dashboard_exibe_pagina_para_cliente(self):
        usuario = User.objects.create_user(username="cliente", password="senha-forte")
        Perfil.objects.create(usuario=usuario, tipo_usuario="cliente")
        self.client.force_login(usuario)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard.html")

    def test_dashboard_cria_perfil_cliente_quando_nao_existe(self):
        usuario = User.objects.create_user(username="sem_perfil", password="senha-forte")
        self.client.force_login(usuario)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        perfil = Perfil.objects.get(usuario=usuario)
        self.assertEqual(perfil.tipo_usuario, "cliente")

    def test_dashboard_redireciona_superadmin_para_django_admin(self):
        usuario = User.objects.create_superuser(
            username="superadministrador",
            email="superadmin@example.com",
            password="senha-forte",
        )
        self.client.force_login(usuario)

        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(response, reverse("admin:index"))

    def test_admin_de_aplicacao_usa_dashboard_mas_nao_entra_no_django_admin(self):
        usuario = User.objects.create_user(
            username="administrador",
            password="senha-forte",
        )
        Perfil.objects.create(
            usuario=usuario,
            tipo_usuario=Perfil.TIPO_ADMINISTRADOR,
        )
        self.client.force_login(usuario)

        dashboard_response = self.client.get(reverse("dashboard"))
        admin_response = self.client.get(reverse("admin:index"))

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, reverse("servicos"))
        self.assertFalse(usuario.is_staff)
        self.assertEqual(admin_response.status_code, 302)
        self.assertEqual(
            admin_response.url,
            f"{reverse('admin:login')}?next={reverse('admin:index')}",
        )

    def test_dashboard_cliente_exibe_apenas_perfil_vitrine_e_pedidos(self):
        usuario = User.objects.create_user(username="cliente-restrito", password="senha-forte")
        Perfil.objects.create(usuario=usuario, tipo_usuario=Perfil.TIPO_CLIENTE)
        self.client.force_login(usuario)

        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, reverse("perfil"))
        self.assertContains(response, reverse("produtos"))
        self.assertContains(response, reverse("meus_pedidos"))
        self.assertNotContains(response, reverse("servicos"))
        self.assertNotContains(response, reverse("contatos"))
        self.assertNotContains(response, reverse("relatorios"))

    def test_visitante_nao_pode_acessar_perfil(self):
        response = self.client.get(reverse("perfil"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('perfil')}",
        )


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetViewTests(TestCase):
    def test_usuario_redefine_senha_pelo_fluxo_nativo_do_django(self):
        usuario = User.objects.create_user(
            username="recuperar",
            email="recuperar@example.com",
            password="Senha-antiga-123!",
        )

        response = self.client.post(
            reverse("password_reset"),
            {"email": usuario.email},
            follow=True,
        )

        self.assertContains(response, "Verifique seu e-mail")
        self.assertEqual(len(mail.outbox), 1)
        reset_url = next(
            line for line in mail.outbox[0].body.splitlines()
            if "/login/senha/redefinir/" in line
        )
        reset_path = urlsplit(reset_url).path

        confirm_response = self.client.get(reset_path, follow=True)
        self.assertEqual(confirm_response.status_code, 200)
        confirm_path = confirm_response.request["PATH_INFO"]
        response = self.client.post(
            confirm_path,
            {
                "new_password1": "Senha-nova-456!",
                "new_password2": "Senha-nova-456!",
            },
            follow=True,
        )

        usuario.refresh_from_db()
        self.assertContains(response, "Senha atualizada")
        self.assertTrue(usuario.check_password("Senha-nova-456!"))
