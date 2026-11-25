from django.urls import path 
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("servicos", views.servicos, name="servicos"),
    path("add-servico", views.addServico, name="addServico"),
    path("excluir-servico/<int:id>", views.excluirServico, name="excluirServico"),
    path("editar-servico/<int:id>", views.editarServico, name="editarServico"),
    path("produtos", views.produtos, name="produtos"),
    path("novo-contato", views.novoContato, name="novoContato"),
    path("contatos", views.contatos, name="contatos"),
    path("excluir-contato/<int:id>", views.excluirContato, name="excluirContato"),
    path("carrinho/adicionar/<int:id>/", views.adicionar_ao_carrinho, name="adicionar_carrinho"),
    path("carrinho/remover/<int:id>/", views.remover_item_carrinho, name="remover_item_carrinho"),
    path("carrinho/comprar/", views.comprar_carrinho, name="comprar_carrinho"),
    path("meus-pedidos/", views.meus_pedidos, name="meus_pedidos"),
    path("remover-pedido/<int:id>/", views.remover_pedido, name="remover_pedido"),
    path("integrantes",views.integrantes, name="integrantes"),
    path("add-integrante", views.addIntegrante, name="addIntegrante"),
    path("editar-integrante/<int:id>", views.editarIntegrante, name="editarIntegrante"),
    path("del-integrante/<int:id>", views.delIntegrante, name="delIntegrante"),
    
    path("categoria-api/", views.categorias_api, name="categorias_api"),
    path("categoria-api/<int:id>", views.categoria_api, name="categoria_api"),
    path("relatorios/",views.relatorios, name='relatorios'),
]
