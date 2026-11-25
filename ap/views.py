from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Sum
from django.db.models.deletion import ProtectedError
from django.db.models.functions import TruncMonth
from django.http import Http404, request
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
import re
from .serializers import CategoriaSerializer
from .models import Asset, Contato, Categoria, ItemPedido, Pedido
from .forms import FormContato, FormServico
from .supabase_client import supabase
from .permissions import AdminOrReadOnly
from login.permissions import administrator_required, is_administrator
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
import os
import requests

# Create your views here.
MAX_INTEGRANTES = 3
RAWG_PIXEL_ART_TAGS = {"pixel-graphics", "pixel-art", "pixelart"}
RAWG_ADULT_CONTENT_TERMS = {
    "adult",
    "adults",
    "erotic",
    "hentai",
    "nsfw",
    "nude",
    "nudity",
    "18+",
    "porn",
    "pornographic",
    "pornography",
    "porno",
    "sexual",
    "xxx",
}


def _is_safe_pixel_art_game(game):
    slug = game.get("slug")
    if not isinstance(slug, str) or not slug.strip():
        return False

    tags = game.get("tags")
    if not isinstance(tags, list):
        return False

    tag_values = []
    for tag in tags:
        if isinstance(tag, dict):
            tag_values.extend(
                value
                for value in (tag.get("slug"), tag.get("name"))
                if isinstance(value, str)
            )

    normalized_values = [
        re.sub(r"[^a-z0-9+]+", "-", value.casefold()).strip("-")
        for value in tag_values
    ]
    if not RAWG_PIXEL_ART_TAGS.intersection(normalized_values):
        return False

    text_values = [game.get("name"), game.get("description_raw"), *tag_values]
    esrb_rating = game.get("esrb_rating")
    if isinstance(esrb_rating, dict):
        text_values.extend(
            value
            for value in (esrb_rating.get("name"), esrb_rating.get("slug"))
            if isinstance(value, str)
        )
    elif isinstance(esrb_rating, str):
        text_values.append(esrb_rating)

    normalized_text = " ".join(
        re.sub(r"[^a-z0-9+]+", " ", value.casefold())
        for value in text_values
        if isinstance(value, str)
    )
    return not RAWG_ADULT_CONTENT_TERMS.intersection(normalized_text.split())

def index(request):
    return render (request, "index.html")

@administrator_required
def servicos(request):
    servicos = Asset.objects.select_related("categoria")
     
    total_servicos = servicos.count()
    tem_servicos = servicos.exists()
    
    mais_barato = servicos.order_by('preco').first()
    mais_caro = servicos.order_by('-preco').first()
    
    
    #recupera o valor do formulário de busca enviado pelo usuário
    busca = request.GET.get('busca')
    if busca:
        servicos = servicos.filter(nome__icontains=busca)
        
    #recupera as categorias ativas para exibir no filtro
    categorias = Categoria.objects.filter(ativo=True)
    
    #recupera o valor do filtro de categoria enviado pelo usuário
    categoria = request.GET.get('categoria')
    if categoria:
        #aplica o filtro de categoria aos serviços
        servicos = servicos.filter(categoria_id=categoria)
        
    preco = request.GET.get('preco')
    if preco == 'baixo':
        servicos = servicos.filter(preco__lte=50)
    elif preco == 'medio':
        servicos = servicos.filter(preco__gt=50, preco__lte=250)
    elif preco == 'alto':
        servicos = servicos.filter(preco__gt=250)
    
    ordem = request.GET.get('ordem')
    if ordem == 'menor':
        servicos = servicos.order_by('preco')
    elif ordem == 'maior':
        servicos = servicos.order_by('-preco')
    elif ordem == 'nome':
        servicos = servicos.order_by('nome')

    contexto = {
        'servicos': servicos,
        'total_servicos': total_servicos,
        'tem_servicos': tem_servicos,
        'mais_barato': mais_barato,
        'mais_caro': mais_caro,
        'busca': busca,
        'categoria': categoria,
        'categorias': categorias,
        'preco': preco,
        'ordem' : ordem,
    }
        
    return render (request, "servicos.html", contexto)

@administrator_required
def addServico(request):
    form = FormServico(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect('servicos')

    return render (request, "add-servico.html", {'form': form})

@administrator_required
@require_POST
def excluirServico(request, id):
    servico = get_object_or_404(Asset, id=id)
    imagem = servico.imagem
    try:
        servico.delete()
    except ProtectedError:
        messages.warning(
            request,
            "Não pode removê-lo. Um usuário está comprando este item.",
        )
        return redirect("servicos")

    if imagem:
        imagem.delete(save=False)
    return redirect('servicos')

@administrator_required
def editarServico(request, id):
    servico = Asset.objects.get(id=id)
    form = FormServico(request.POST or None, request.FILES or None, instance=servico)
    if request.POST:
        if form.is_valid():
            form.save()
            return redirect('servicos')

    return render (request, "editar-servico.html", {'form': form})

def produtos(request):
    produtos = Asset.objects.filter(ativo=True)

    produtos_api = []
    erro_api_rawg = None
    rawg_api_key = os.getenv("RAWG_API_KEY")
    if not rawg_api_key:
        erro_api_rawg = "Configure RAWG_API_KEY no arquivo .env para carregar os jogos."
    else:
        try:
            resposta = requests.get(
                "https://api.rawg.io/api/games",
                params={
                    "key": rawg_api_key,
                    "page_size": 12,
                    "ordering": "-rating",
                    "tags": "pixel-graphics",
                },
                timeout=10,
            )
            resposta.raise_for_status()
            payload = resposta.json()
            resultados = payload.get("results") if isinstance(payload, dict) else None
            if not isinstance(resultados, list) or any(
                not isinstance(jogo, dict) for jogo in resultados
            ):
                raise ValueError("Formato de resposta inválido da RAWG.")
            produtos_api = [
                jogo for jogo in resultados if _is_safe_pixel_art_game(jogo)
            ]
        except ValueError:
            erro_api_rawg = "A RAWG retornou uma resposta inválida. Tente novamente mais tarde."
        except requests.HTTPError as erro:
            if erro.response is not None and erro.response.status_code in (401, 403):
                erro_api_rawg = "A RAWG rejeitou a chave. Confira RAWG_API_KEY no arquivo .env."
            else:
                erro_api_rawg = "A RAWG está indisponível no momento. Tente novamente mais tarde."
        except requests.RequestException:
            erro_api_rawg = "Não foi possível conectar à RAWG. Tente novamente mais tarde."

    adquiridos = set()
    no_carrinho = set()
    if request.user.is_authenticated:
        adquiridos = set(
            ItemPedido.objects.filter(
                pedido__usuario=request.user,
                pedido__status=Pedido.STATUS_PAGO,
            ).values_list("asset_id", flat=True)
        )
        no_carrinho = set(
            ItemPedido.objects.filter(
                pedido__usuario=request.user,
                pedido__status=Pedido.STATUS_PENDENTE,
            ).values_list("asset_id", flat=True)
        )

    return render(request, "produtos.html", {
        "produtos": produtos,
        "produtos_api": produtos_api,
        "erro_api_rawg": erro_api_rawg,
        "adquiridos": adquiridos,
        "no_carrinho": no_carrinho,
    })


@login_required
@require_POST
def adicionar_ao_carrinho(request, id):
    with transaction.atomic():
        asset = get_object_or_404(Asset.objects.select_for_update(), id=id)
        if not asset.ativo:
            messages.warning(request, "Este asset não está mais disponível para compra.")
            return redirect("produtos")

        ja_adquirido = ItemPedido.objects.select_for_update().filter(
            pedido__usuario=request.user,
            pedido__status=Pedido.STATUS_PAGO,
            asset=asset,
        ).exists()
        if ja_adquirido:
            messages.warning(request, "Você já adquiriu este asset.")
            return redirect("meus_pedidos")

        carrinho, _ = Pedido.objects.get_or_create(
            usuario=request.user,
            status=Pedido.STATUS_PENDENTE,
            defaults={"oculto": False},
        )
        _, item_criado = ItemPedido.objects.get_or_create(
            pedido=carrinho,
            asset=asset,
            defaults={"preco_unitario": asset.preco},
        )

    if item_criado:
        messages.success(request, "Asset adicionado ao carrinho.")
    else:
        messages.info(request, "Este asset já está no seu carrinho.")
    return redirect("meus_pedidos")


@login_required
@require_POST
def remover_item_carrinho(request, id):
    item = get_object_or_404(
        ItemPedido,
        id=id,
        pedido__usuario=request.user,
        pedido__status=Pedido.STATUS_PENDENTE,
    )
    item.delete()
    messages.success(request, "Asset removido do carrinho.")
    return redirect("meus_pedidos")


@login_required
@require_POST
def comprar_carrinho(request):
    with transaction.atomic():
        carrinho = get_object_or_404(
            Pedido.objects.select_for_update(),
            usuario=request.user,
            status=Pedido.STATUS_PENDENTE,
            oculto=False,
        )
        itens = list(carrinho.itens.select_related("asset"))
        if not itens:
            messages.warning(request, "Seu carrinho está vazio.")
            return redirect("meus_pedidos")

        asset_ids = [item.asset_id for item in itens]
        if Asset.objects.filter(id__in=asset_ids, ativo=False).exists():
            messages.warning(
                request,
                "Um ou mais assets do carrinho não estão mais disponíveis. Remova-os antes de continuar.",
            )
            return redirect("meus_pedidos")

        ja_adquirido = ItemPedido.objects.filter(
            pedido__usuario=request.user,
            pedido__status=Pedido.STATUS_PAGO,
            asset_id__in=asset_ids,
        ).exists()
        if ja_adquirido:
            messages.warning(
                request,
                "Um asset do carrinho já foi adquirido. Remova-o para evitar uma compra duplicada.",
            )
            return redirect("meus_pedidos")

        total = carrinho.total()
        carrinho.status = Pedido.STATUS_PAGO
        carrinho.save(update_fields=["status"])

    messages.success(request, f"Compra concluída. Total: R$ {total:.2f}.")
    return redirect("meus_pedidos")


@login_required
def meus_pedidos(request):
    carrinho = (
        Pedido.objects.filter(
            usuario=request.user,
            status=Pedido.STATUS_PENDENTE,
            oculto=False,
        )
        .prefetch_related("itens__asset")
        .first()
    )
    pedidos = (
        Pedido.objects.filter(
            usuario=request.user,
            oculto=False,
        )
        .exclude(status=Pedido.STATUS_PENDENTE)
        .prefetch_related("itens__asset")
        .order_by("-criado_em")
    )
    pedidos_ocultos = Pedido.objects.filter(
        usuario=request.user,
        status=Pedido.STATUS_PAGO,
        oculto=True,
    ).exists()
    return render(request, "meus-pedidos.html", {
        "carrinho": carrinho,
        "pedidos": pedidos,
        "pedidos_ocultos": pedidos_ocultos,
    })


@login_required
@require_POST
def remover_pedido(request, id):
    pedido = get_object_or_404(
        Pedido,
        id=id,
        usuario=request.user,
        status=Pedido.STATUS_PAGO,
        oculto=False,
    )
    pedido.oculto = True
    pedido.save(update_fields=["oculto"])
    messages.success(
        request,
        "Pedido removido da sua lista. A compra foi preservada e não poderá ser feita novamente.",
    )
    return redirect("meus_pedidos")

@administrator_required
def contatos(request):
    contatos = Contato.objects.all()
    return render(request, "contatos.html", {'contatos': contatos})

def novoContato(request):
    if request.method == "POST":
        form = FormContato(request.POST)
        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        form = FormContato()
    
    return render(request, "novo-contato.html", {'form': form})

@administrator_required
@require_POST
def excluirContato(request, id):
    contato = Contato.objects.get(id=id)
    contato.delete()
    return redirect('contatos')

def integrantes(request):
    resposta = supabase.table("integrantes").select("*").execute()
    integrantes = resposta.data
    administrador = is_administrator(request.user)
    pode_adicionar = administrador and len(integrantes) < MAX_INTEGRANTES
    equipe_completa = administrador and len(integrantes) >= MAX_INTEGRANTES
    return render(request, "integrantes.html", {
        "integrantes": integrantes,
        "pode_adicionar_integrante": pode_adicionar,
        "equipe_completa": equipe_completa,
    })

@administrator_required
def addIntegrante(request):
    resposta = supabase.table("integrantes").select("id").execute()
    if len(resposta.data) >= MAX_INTEGRANTES:
        messages.warning(request, "A equipe já atingiu o limite de 3 integrantes.")
        return redirect("integrantes")

    if request.method == "POST":
        nome = request.POST.get("nome")
        cargo = request.POST.get("cargo")
        biografia = request.POST.get("biografia")
        foto_url = request.POST.get("foto_url")
        
        supabase.table("integrantes").insert({
            "nome": nome,
            "cargo": cargo,
            "biografia": biografia,
            "foto_url": foto_url
        }).execute()

        messages.success(request, "Integrante adicionado à equipe.")
        return redirect('integrantes')
    
    return render(request, "add-integrante.html")

@administrator_required
def editarIntegrante(request, id):
    resposta = supabase.table("integrantes").select("*").eq("id", id).execute()
    if not resposta.data:
        raise Http404("Integrante não encontrado.")

    integrante = resposta.data[0]
    if request.method == "POST":
        supabase.table("integrantes").update({
            "nome": request.POST.get("nome"),
            "cargo": request.POST.get("cargo"),
            "biografia": request.POST.get("biografia"),
            "foto_url": request.POST.get("foto_url"),
        }).eq("id", id).execute()
        messages.success(request, "Integrante atualizado.")
        return redirect("integrantes")

    return render(request, "editar-integrante.html", {"integrante": integrante})

@administrator_required
@require_POST
def delIntegrante(request, id):
    supabase.table("integrantes").delete().eq("id", id).execute()
    messages.success(request, "Integrante removido da equipe.")
    return redirect('integrantes')

@api_view(['GET', 'POST'])
@permission_classes([AdminOrReadOnly])
def categorias_api(request):
    if request.method=='GET':
        categorias = Categoria.objects.all()
        serializer = CategoriaSerializer(categorias, many=True)
        return Response(serializer.data)
    elif request.method=='POST':
        serializer = CategoriaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'DELETE', 'PUT'])
@permission_classes([AdminOrReadOnly])
def categoria_api(request, id):
    categoria = Categoria.objects.get(id=id)
    if request.method == 'GET':
        serializer = CategoriaSerializer(categoria)
        return Response(serializer.data)
    elif request.method=='DELETE':
        categoria.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    elif request.method == 'PUT':
        serializer = CategoriaSerializer(categoria, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
@administrator_required
def relatorios(request):
    servicos = Asset.objects.all()
    servicos_ativos = servicos.filter(ativo=True).count()
    servicos_inativos = servicos.filter(ativo=False).count()

    categorias = servicos.values('categoria__nome').annotate(quantidade=Count('id'))

    vendas_por_categoria = (
        ItemPedido.objects
        .filter(pedido__status=Pedido.STATUS_PAGO)
        .values("asset__categoria__nome")
        .annotate(total=Sum("preco_unitario"))
        .order_by("asset__categoria__nome")
    )
    pedidos_por_mes = (
        Pedido.objects.filter(status=Pedido.STATUS_PAGO)
        .annotate(mes=TruncMonth("criado_em"))
        .values("mes")
        .annotate(quantidade=Count("id"))
        .order_by("mes")
    )

    return render(request, 'relatorios.html', {
        'servicos_ativos': servicos_ativos,
        'servicos_inativos': servicos_inativos,
        'status_valores': [servicos_ativos, servicos_inativos],
        'categorias_labels': [
            item['categoria__nome'] or 'Sem categoria'
            for item in categorias
        ],
        'categorias_valores': [
            item['quantidade']
            for item in categorias
        ],
        'vendas_labels': [
            item['asset__categoria__nome'] or 'Sem categoria'
            for item in vendas_por_categoria
        ],
        'vendas_valores': [
            float(item['total'] or 0)
            for item in vendas_por_categoria
        ],
        'meses_labels': [
            item['mes'].strftime("%m/%Y") if item['mes'] else ""
            for item in pedidos_por_mes
        ],
        'meses_valores': [
            item['quantidade']
            for item in pedidos_por_mes
        ],
    })