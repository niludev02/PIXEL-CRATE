Chart.defaults.color = '#F2EFFF';

const categorias = JSON.parse(document.getElementById('categorias').textContent);
const quantidades = JSON.parse(document.getElementById('quantidades').textContent);
const statusValores = JSON.parse(document.getElementById('status-valores').textContent);
const vendasCategorias = JSON.parse(document.getElementById('vendas-categorias').textContent);
const vendasValores = JSON.parse(document.getElementById('vendas-valores').textContent);
const meses = JSON.parse(document.getElementById('meses').textContent);
const pedidosMes = JSON.parse(document.getElementById('pedidos-mes').textContent);

    new Chart(document.getElementById('graficoCategorias'),{
        type: 'bar',
        data: {
            labels: categorias,
            datasets:[{
                label: 'Assets por categoria',
                data: quantidades,
                backgroundColor: '#7C5CFF'
            }]

        }
    });

    new Chart(document.getElementById('graficoStatus'),{
        type:'doughnut',
        data: {
            labels: ['Ativos', 'Inativos'],
            datasets:[{
                label: 'Assets por status',
                data: statusValores,
                backgroundColor: [
                    '#7C5CFF',
                    '#3DDC97'
                ]
            }]
        }
    });

new Chart(document.getElementById('graficoVendas'), {
    type: 'bar',
    data: {
        labels: vendasCategorias,
        datasets: [{
            label: 'Total vendido por categoria',
            data: vendasValores,
            backgroundColor: '#7C5CFF'
        }]
    }
});

new Chart(document.getElementById('graficoMeses'), {
    type: 'line',
    data: {
        labels: meses,
        datasets: [{
            label: 'Pedidos por mês',
            data: pedidosMes,
            borderColor: '#3DDC97',
            backgroundColor: '#3DDC97'
        }]
    }
});