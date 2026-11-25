from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db.models.fields.files import FieldFile
from django.test import TestCase
from django.urls import reverse
from requests import RequestException

from login.models import Perfil

from .forms import FormServico
from .models import Asset, Categoria, ItemPedido, Pedido
from .storage import SupabasePublicMediaStorage


def create_admin_user(username, password="senha-segura"):
    user = User.objects.create_user(username=username, password=password)
    Perfil.objects.create(
        usuario=user,
        tipo_usuario=Perfil.TIPO_ADMINISTRADOR,
    )
    return user


class SupabasePreviewStorageTests(TestCase):
    @patch("ap.storage.supabase")
    def test_save_uploads_preview_with_unique_name_and_image_content_type(self, supabase_mock):
        bucket = supabase_mock.storage.from_.return_value
        storage = SupabasePublicMediaStorage(bucket_name="pixelcrate-previews")

        saved_name = storage.save(
            "servicos/preview.png",
            ContentFile(b"image-bytes"),
        )

        uploaded_name, uploaded_content = bucket.upload.call_args.args
        self.assertRegex(uploaded_name, r"^servicos/[0-9a-f]{32}\.png$")
        self.assertEqual(uploaded_name, saved_name)
        self.assertEqual(uploaded_content, b"image-bytes")
        self.assertEqual(
            bucket.upload.call_args.kwargs["file_options"],
            {"content-type": "image/png", "upsert": "false"},
        )
        supabase_mock.storage.from_.assert_called_once_with("pixelcrate-previews")

    @patch("ap.storage.supabase")
    def test_preview_url_comes_from_supabase_public_bucket(self, supabase_mock):
        bucket = supabase_mock.storage.from_.return_value
        bucket.get_public_url.return_value = "https://storage.example/preview.png"
        storage = SupabasePublicMediaStorage(bucket_name="pixelcrate-previews")

        url = storage.url("servicos/preview.png")

        self.assertEqual(url, "https://storage.example/preview.png")
        bucket.get_public_url.assert_called_once_with("servicos/preview.png")


class IntegrantesAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="equipe", password="senha-segura")
        self.admin = create_admin_user("admin-equipe")

    @patch("ap.views.supabase")
    def test_visitante_can_view_team_without_management_actions(self, supabase_mock):
        supabase_mock.table.return_value.select.return_value.execute.return_value = (
            SimpleNamespace(data=[{
                "id": 1,
                "nome": "Ana",
                "cargo": "Designer",
                "biografia": "Cria os visuais do projeto.",
                "foto_url": "",
            }])
        )

        response = self.client.get(reverse("integrantes"))

        self.assertContains(response, "Ana")
        self.assertNotContains(response, "Adicionar integrante")
        self.assertNotContains(response, "Editar")
        self.assertNotContains(response, "Excluir")

    def test_guest_is_redirected_from_integrante_management(self):
        response = self.client.get(reverse("addIntegrante"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('addIntegrante')}",
        )

    @patch("ap.views.supabase")
    def test_guest_sees_construction_notice_but_no_add_button(self, supabase_mock):
        supabase_mock.table.return_value.select.return_value.execute.return_value = (
            SimpleNamespace(data=[])
        )

        response = self.client.get(reverse("integrantes"))

        self.assertContains(response, "Equipe em construção")
        self.assertNotContains(response, "Adicionar integrante")

    @patch("ap.views.supabase")
    def test_admin_can_start_the_empty_team(self, supabase_mock):
        self.client.force_login(self.admin)
        supabase_mock.table.return_value.select.return_value.execute.return_value = (
            SimpleNamespace(data=[])
        )

        response = self.client.get(reverse("integrantes"))

        self.assertContains(response, "Adicionar integrante")
        self.assertContains(response, "Equipe em construção")
        self.assertEqual(self.client.get(reverse("addIntegrante")).status_code, 200)

    @patch("ap.views.supabase")
    def test_admin_can_add_an_integrante(self, supabase_mock):
        self.client.force_login(self.admin)
        supabase_mock.table.return_value.select.return_value.execute.return_value = (
            SimpleNamespace(data=[{"id": 1}])
        )

        response = self.client.post(reverse("addIntegrante"), {
            "nome": "Bruno",
            "cargo": "Desenvolvedor",
            "biografia": "Cria experiências para o projeto.",
            "foto_url": "",
        })

        self.assertRedirects(response, reverse("integrantes"))
        supabase_mock.table.return_value.insert.assert_called_once_with({
            "nome": "Bruno",
            "cargo": "Desenvolvedor",
            "biografia": "Cria experiências para o projeto.",
            "foto_url": "",
        })

    @patch("ap.views.supabase")
    def test_admin_cannot_add_more_than_three_integrantes(self, supabase_mock):
        self.client.force_login(self.admin)
        supabase_mock.table.return_value.select.return_value.execute.return_value = (
            SimpleNamespace(data=[{"id": 1}, {"id": 2}, {"id": 3}])
        )

        response = self.client.post(reverse("addIntegrante"), {
            "nome": "Bruno",
            "cargo": "Dev",
            "biografia": "Desenvolvedor",
        })

        self.assertRedirects(response, reverse("integrantes"))
        supabase_mock.table.return_value.insert.assert_not_called()

    def test_client_cannot_manage_the_team(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("addIntegrante"))

        self.assertRedirects(response, reverse("dashboard"))
        self.assertFalse(response.wsgi_request.user.is_staff)


class AssetScreenTests(TestCase):
    def test_asset_management_shows_active_free_and_inactive_assets(self):
        admin = create_admin_user("admin-assets")
        self.client.force_login(admin)
        Asset.objects.create(nome="Asset grátis", descricao="", preco=0, ativo=True)
        Asset.objects.create(nome="Asset oculto", descricao="", preco=25, ativo=False)

        response = self.client.get(reverse("servicos"))

        self.assertContains(response, "Asset grátis")
        self.assertContains(response, "Asset oculto")
        self.assertContains(response, "Ativo")
        self.assertContains(response, "Inativo")
        self.assertContains(response, "Assets cadastrados")
        self.assertContains(response, "Menor preço")
        self.assertContains(response, "Maior preço")
        self.assertContains(response, "Buscar por nome do asset")
        self.assertContains(response, "Adicionar asset")

    def test_client_cannot_open_asset_management(self):
        client_user = User.objects.create_user(
            username="cliente-sem-gestao",
            password="senha-segura",
        )
        self.client.force_login(client_user)

        response = self.client.get(reverse("servicos"))

        self.assertRedirects(response, reverse("dashboard"))

    def test_client_cannot_mutate_categories_api(self):
        client_user = User.objects.create_user(
            username="cliente-categoria",
            password="senha-segura",
        )
        self.client.force_login(client_user)

        response = self.client.post(
            reverse("categorias_api"),
            {"nome": "Categoria bloqueada"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Categoria.objects.filter(nome="Categoria bloqueada").exists())

    def test_inactive_purchased_asset_is_hidden_from_products_but_kept_in_order_history(self):
        user = User.objects.create_user(username="historico-asset", password="senha-segura")
        asset = Asset.objects.create(
            nome="Mouse Ergonomico",
            descricao="",
            preco=0,
            ativo=False,
        )
        pedido = Pedido.objects.create(usuario=user)
        ItemPedido.objects.create(pedido=pedido, asset=asset, preco_unitario=asset.preco)
        self.client.force_login(user)

        with patch.dict("os.environ", {"RAWG_API_KEY": ""}):
            products_response = self.client.get(reverse("produtos"))
        orders_response = self.client.get(reverse("meus_pedidos"))

        self.assertNotContains(products_response, "Mouse Ergonomico")
        self.assertContains(orders_response, "Mouse Ergonomico")

    def test_asset_form_uses_field_verbose_names_as_labels(self):
        form = FormServico()

        self.assertEqual(form.fields["nome"].label, "Nome do asset")
        self.assertEqual(form.fields["ativo"].label, "Ativo (aparece na vitrine)")

    @patch("ap.views.requests.get")
    def test_unpurchased_active_asset_has_an_add_to_cart_button(self, requests_mock):
        requests_mock.return_value.json.return_value = {
            "results": [{
                "slug": "jogo-rawg-de-teste",
                "name": "Jogo RAWG de teste",
                "background_image": "https://example.test/jogo.jpg",
                "released": "2026-01-01",
                "rating": 4.5,
                "metacritic": 88,
                "tags": [{"name": "Pixel Graphics", "slug": "pixel-graphics"}],
            }]
        }
        user = User.objects.create_user(username="comprador-novo", password="senha-segura")
        asset = Asset.objects.create(nome="Novo asset", descricao="", preco=20)
        self.client.force_login(user)

        with patch.dict("os.environ", {"RAWG_API_KEY": "chave-de-teste"}):
            response = self.client.get(reverse("produtos"))

        self.assertContains(response, "Adicionar ao carrinho")
        self.assertContains(response, "Jogo RAWG de teste")
        self.assertContains(response, "Metacritic: 88/100")
        self.assertContains(response, 'href="https://rawg.io/games/jogo-rawg-de-teste"')
        self.assertContains(
            response,
            f'action="{reverse("adicionar_carrinho", args=[asset.pk])}"',
        )
        self.assertNotContains(response, "Já adquirido")
        requests_mock.assert_called_once_with(
            "https://api.rawg.io/api/games",
            params={
                "key": "chave-de-teste",
                "page_size": 12,
                "ordering": "-rating",
                "tags": "pixel-graphics",
            },
            timeout=10,
        )

    @patch("ap.views.requests.get")
    def test_rawg_only_displays_pixel_art_and_hides_adult_games(self, requests_mock):
        requests_mock.return_value.json.return_value = {
            "results": [
                {
                    "slug": "pixel-adventure",
                    "name": "Pixel Adventure",
                    "tags": [{"name": "Pixel Graphics", "slug": "pixel-graphics"}],
                },
                {
                    "slug": "hentai-pixel-game",
                    "name": "Hentai Pixel Game",
                    "tags": [
                        {"name": "Pixel Graphics", "slug": "pixel-graphics"},
                        {"name": "Hentai", "slug": "hentai"},
                    ],
                },
                {
                    "slug": "pornographic-pixel-game",
                    "name": "Pornographic Pixel Game",
                    "tags": [
                        {"name": "Pixel Graphics", "slug": "pixel-graphics"},
                        {"name": "Porn", "slug": "porn"},
                    ],
                },
                {
                    "slug": "adult-pixel-game",
                    "name": "Adult Pixel Game",
                    "tags": [{"name": "Pixel Graphics", "slug": "pixel-graphics"}],
                    "esrb_rating": {"name": "Adults Only", "slug": "adults-only"},
                },
                {
                    "slug": "regular-adventure",
                    "name": "Regular Adventure",
                    "tags": [{"name": "Adventure", "slug": "adventure"}],
                },
            ]
        }

        with patch.dict("os.environ", {"RAWG_API_KEY": "chave-de-teste"}):
            response = self.client.get(reverse("produtos"))

        self.assertContains(response, "Pixel Adventure")
        self.assertNotContains(response, "Hentai Pixel Game")
        self.assertNotContains(response, "Pornographic Pixel Game")
        self.assertNotContains(response, "Adult Pixel Game")
        self.assertNotContains(response, "Regular Adventure")

    def test_asset_linked_to_order_cannot_be_deleted(self):
        user = create_admin_user("admin-assets-com-venda")
        asset = Asset.objects.create(nome="Asset comprado", descricao="", preco=20)
        pedido = Pedido.objects.create(usuario=user)
        ItemPedido.objects.create(pedido=pedido, asset=asset, preco_unitario=asset.preco)
        self.client.force_login(user)

        list_response = self.client.get(reverse("servicos"))
        self.assertContains(list_response, 'class="btn btn-excluir">Excluir</button>')
        self.assertNotContains(list_response, "disabled")

        with patch.object(FieldFile, "delete") as delete_image:
            response = self.client.post(
                reverse("excluirServico", args=[asset.pk]),
                follow=True,
            )

        delete_image.assert_not_called()
        self.assertContains(response, "Não pode removê-lo. Um usuário está comprando este item.")
        self.assertTrue(Asset.objects.filter(pk=asset.pk).exists())

    @patch("ap.views.requests.get")
    def test_asset_already_in_an_order_cannot_be_added_to_cart_again(self, requests_mock):
        requests_mock.return_value.json.return_value = {"results": []}
        user = User.objects.create_user(username="comprador", password="senha-segura")
        asset = Asset.objects.create(nome="Asset adquirido", descricao="", preco=20)
        pedido = Pedido.objects.create(usuario=user)
        ItemPedido.objects.create(pedido=pedido, asset=asset, preco_unitario=asset.preco)
        self.client.force_login(user)

        with patch.dict("os.environ", {"RAWG_API_KEY": "chave-de-teste"}):
            product_response = self.client.get(reverse("produtos"))
        self.assertContains(product_response, "Já adquirido")
        self.assertNotContains(
            product_response,
            reverse("adicionar_carrinho", args=[asset.pk]),
        )

        response = self.client.post(
            reverse("adicionar_carrinho", args=[asset.pk]),
            follow=True,
        )

        self.assertContains(response, "Você já adquiriu este asset.")
        self.assertEqual(Pedido.objects.filter(usuario=user).count(), 1)
        self.assertEqual(ItemPedido.objects.filter(pedido__usuario=user).count(), 1)

    def test_inactive_asset_shows_a_warning_when_added_from_a_stale_page(self):
        user = User.objects.create_user(username="asset-desativado", password="senha-segura")
        asset = Asset.objects.create(nome="Asset indisponível", descricao="", preco=20)
        asset.ativo = False
        asset.save()
        self.client.force_login(user)

        response = self.client.post(
            reverse("adicionar_carrinho", args=[asset.pk]),
            follow=True,
        )

        self.assertContains(response, "Este asset não está mais disponível para compra.")
        self.assertFalse(Pedido.objects.filter(usuario=user).exists())

    def test_adding_assets_creates_one_pending_cart_and_prevents_duplicate_items(self):
        user = User.objects.create_user(username="carrinho", password="senha-segura")
        first_asset = Asset.objects.create(nome="Asset um", descricao="", preco=20)
        second_asset = Asset.objects.create(nome="Asset dois", descricao="", preco=35)
        self.client.force_login(user)

        for asset in (first_asset, second_asset, first_asset):
            response = self.client.post(reverse("adicionar_carrinho", args=[asset.pk]))
            self.assertRedirects(response, reverse("meus_pedidos"))

        carrinhos = Pedido.objects.filter(
            usuario=user,
            status=Pedido.STATUS_PENDENTE,
        )
        self.assertEqual(carrinhos.count(), 1)
        carrinho = carrinhos.get()
        self.assertEqual(carrinho.itens.count(), 2)
        self.assertEqual(carrinho.total(), first_asset.preco + second_asset.preco)

        response = self.client.get(reverse("meus_pedidos"))
        self.assertContains(response, "Calcular total e comprar tudo")
        self.assertContains(response, "R$ 55,00")

    def test_checkout_purchases_all_cart_items_at_once(self):
        user = User.objects.create_user(username="checkout", password="senha-segura")
        first_asset = Asset.objects.create(nome="Asset A", descricao="", preco=12)
        second_asset = Asset.objects.create(nome="Asset B", descricao="", preco=18)
        carrinho = Pedido.objects.create(usuario=user, status=Pedido.STATUS_PENDENTE)
        ItemPedido.objects.create(pedido=carrinho, asset=first_asset, preco_unitario=first_asset.preco)
        ItemPedido.objects.create(pedido=carrinho, asset=second_asset, preco_unitario=second_asset.preco)
        self.client.force_login(user)

        response = self.client.post(reverse("comprar_carrinho"), follow=True)

        carrinho.refresh_from_db()
        self.assertEqual(carrinho.status, Pedido.STATUS_PAGO)
        self.assertEqual(carrinho.total(), first_asset.preco + second_asset.preco)
        self.assertEqual(carrinho.itens.count(), 2)
        self.assertFalse(
            Pedido.objects.filter(usuario=user, status=Pedido.STATUS_PENDENTE).exists()
        )
        self.assertContains(response, "Compra concluída. Total: R$ 30.00.")
        self.assertContains(response, "Asset A")
        self.assertContains(response, "Asset B")

    def test_checkout_keeps_cart_pending_when_an_asset_is_inactive(self):
        user = User.objects.create_user(username="asset-inativo", password="senha-segura")
        asset = Asset.objects.create(nome="Asset indisponível", descricao="", preco=20)
        carrinho = Pedido.objects.create(usuario=user, status=Pedido.STATUS_PENDENTE)
        ItemPedido.objects.create(pedido=carrinho, asset=asset, preco_unitario=asset.preco)
        asset.ativo = False
        asset.save()
        self.client.force_login(user)

        response = self.client.post(reverse("comprar_carrinho"), follow=True)

        carrinho.refresh_from_db()
        self.assertEqual(carrinho.status, Pedido.STATUS_PENDENTE)
        self.assertTrue(ItemPedido.objects.filter(pedido=carrinho, asset=asset).exists())
        self.assertContains(response, "não estão mais disponíveis")

    def test_cart_item_can_only_be_removed_by_its_owner(self):
        owner = User.objects.create_user(username="dono-carrinho", password="senha-segura")
        other_user = User.objects.create_user(username="outro-carrinho", password="senha-segura")
        asset = Asset.objects.create(nome="Asset carrinho", descricao="", preco=20)
        carrinho = Pedido.objects.create(usuario=owner, status=Pedido.STATUS_PENDENTE)
        item = ItemPedido.objects.create(
            pedido=carrinho,
            asset=asset,
            preco_unitario=asset.preco,
        )
        self.client.force_login(other_user)

        response = self.client.post(reverse("remover_item_carrinho", args=[item.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(ItemPedido.objects.filter(pk=item.pk).exists())

        self.client.force_login(owner)
        response = self.client.post(reverse("remover_item_carrinho", args=[item.pk]))

        self.assertRedirects(response, reverse("meus_pedidos"))
        self.assertFalse(ItemPedido.objects.filter(pk=item.pk).exists())

    def test_pending_cart_is_not_counted_as_a_sale_in_reports(self):
        user = create_admin_user("admin-relatorio-carrinho")
        categoria = Categoria.objects.create(nome="Modelagem")
        asset = Asset.objects.create(
            nome="Asset vendido",
            descricao="",
            preco=20,
            categoria=categoria,
        )
        compra = Pedido.objects.create(usuario=user, status=Pedido.STATUS_PAGO)
        carrinho = Pedido.objects.create(usuario=user, status=Pedido.STATUS_PENDENTE)
        ItemPedido.objects.create(pedido=compra, asset=asset, preco_unitario=20)
        ItemPedido.objects.create(pedido=carrinho, asset=asset, preco_unitario=20)
        self.client.force_login(user)

        response = self.client.get(reverse("relatorios"))

        self.assertEqual(response.context["vendas_valores"], [20.0])
        self.assertEqual(response.context["meses_valores"], [1])

    @patch("ap.views.requests.get", side_effect=RequestException("RAWG indisponível"))
    def test_products_page_shows_partner_api_failure_state(self, requests_mock):
        with patch.dict("os.environ", {"RAWG_API_KEY": "chave-de-teste"}):
            response = self.client.get(reverse("produtos"))

        self.assertContains(response, "Não foi possível conectar à RAWG.")
        self.assertContains(response, "Nossos assets")

    @patch("ap.views.requests.get")
    def test_products_page_explains_when_rawg_key_is_missing(self, requests_mock):
        with patch.dict("os.environ", {"RAWG_API_KEY": ""}):
            response = self.client.get(reverse("produtos"))

        requests_mock.assert_not_called()
        self.assertContains(response, "Configure RAWG_API_KEY no arquivo .env")

    def test_empty_orders_page_links_to_products(self):
        user = User.objects.create_user(username="comprador", password="senha-segura")
        self.client.force_login(user)

        response = self.client.get(reverse("meus_pedidos"))

        self.assertContains(response, "Você ainda não comprou nenhum asset.")
        self.assertContains(response, reverse("produtos"))

    @patch("ap.views.requests.get")
    def test_removing_order_hides_it_without_allowing_a_duplicate_purchase(self, requests_mock):
        requests_mock.return_value.json.return_value = {"results": []}
        user = User.objects.create_user(username="cliente-pedido", password="senha-segura")
        asset = Asset.objects.create(nome="Asset adquirido", descricao="", preco=20)
        pedido = Pedido.objects.create(usuario=user)
        ItemPedido.objects.create(pedido=pedido, asset=asset, preco_unitario=asset.preco)
        self.client.force_login(user)

        removal_response = self.client.post(
            reverse("remover_pedido", args=[pedido.pk]),
            follow=True,
        )

        self.assertContains(removal_response, "Pedido removido da sua lista.")
        self.assertNotContains(removal_response, f"Pedido #{pedido.pk}")
        pedido.refresh_from_db()
        self.assertTrue(pedido.oculto)
        self.assertTrue(ItemPedido.objects.filter(pedido=pedido, asset=asset).exists())

        with patch.dict("os.environ", {"RAWG_API_KEY": "chave-de-teste"}):
            products_response = self.client.get(reverse("produtos"))
        self.assertContains(products_response, "Já adquirido")
        self.assertNotContains(
            products_response,
            reverse("adicionar_carrinho", args=[asset.pk]),
        )

        duplicate_response = self.client.post(
            reverse("adicionar_carrinho", args=[asset.pk]),
            follow=True,
        )
        self.assertContains(duplicate_response, "Você já adquiriu este asset.")
        self.assertEqual(Pedido.objects.filter(usuario=user).count(), 1)

    def test_user_cannot_remove_another_users_order(self):
        owner = User.objects.create_user(username="dono-pedido", password="senha-segura")
        other_user = User.objects.create_user(username="outro-cliente", password="senha-segura")
        pedido = Pedido.objects.create(usuario=owner)
        self.client.force_login(other_user)

        response = self.client.post(reverse("remover_pedido", args=[pedido.pk]))

        self.assertEqual(response.status_code, 404)
        pedido.refresh_from_db()
        self.assertFalse(pedido.oculto)


class NavigationMenuTests(TestCase):
    def test_guest_menu_offers_login_and_registration(self):
        response = self.client.get(reverse("index"))

        self.assertContains(response, f'href="{reverse("login")}"')
        self.assertContains(response, f'href="{reverse("cadastrar_usuario")}"')
        self.assertNotContains(response, f'href="{reverse("servicos")}"')

    def test_client_menu_and_dashboard_only_expose_customer_pages(self):
        user = User.objects.create_user(username="cliente", password="senha-segura")
        self.client.force_login(user)

        menu_response = self.client.get(reverse("index"))
        self.assertContains(menu_response, f'href="{reverse("meus_pedidos")}"')
        self.assertContains(menu_response, f'href="{reverse("dashboard")}"')
        self.assertContains(menu_response, 'aria-label="Carrinho e meus pedidos"')
        self.assertContains(menu_response, "Editar perfil")
        self.assertContains(menu_response, 'class="logout-button">Sair</button>')
        self.assertNotContains(menu_response, ">Meus pedidos</a>")
        self.assertNotContains(menu_response, ">Perfil</a>")
        self.assertNotContains(menu_response, f'href="{reverse("servicos")}"')
        self.assertNotContains(menu_response, f'href="{reverse("contatos")}"')

        dashboard_response = self.client.get(reverse("dashboard"))
        for route_name in ("produtos", "meus_pedidos", "perfil"):
            self.assertContains(dashboard_response, f'href="{reverse(route_name)}"')
        for label in ("Contatos", "Relatórios"):
            self.assertNotContains(dashboard_response, label)

    def test_admin_menu_exposes_management_pages(self):
        admin = create_admin_user("admin-menu")
        self.client.force_login(admin)

        response = self.client.get(reverse("index"))

        for route_name in (
            "dashboard",
            "servicos",
            "contatos",
            "integrantes",
            "relatorios",
            "perfil",
            "meus_pedidos",
        ):
            self.assertContains(response, f'href="{reverse(route_name)}"')
        self.assertContains(response, 'aria-label="Carrinho e meus pedidos"')
