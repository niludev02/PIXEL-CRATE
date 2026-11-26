Chart.defaults.color = '#A5A6AD';
Chart.defaults.font.family = 'Inter, sans-serif';
Chart.defaults.plugins.legend.labels.usePointStyle = true;

const categorias = JSON.parse(document.getElementById('categorias').textContent);
const quantidades = JSON.parse(document.getElementById('quantidades').textContent);
const statusValores = JSON.parse(document.getElementById('status-valores').textContent);
const vendasCategorias = JSON.parse(document.getElementById('vendas-categorias').textContent);
const vendasValores = JSON.parse(document.getElementById('vendas-valores').textContent);
const meses = JSON.parse(document.getElementById('meses').textContent);
const pedidosMes = JSON.parse(document.getElementById('pedidos-mes').textContent);

const gridColor = 'rgba(165, 166, 173, 0.14)';
const categoryColors = {
    green: '#A9C987',
    purple: '#9B87F5',
    gold: '#E8BD70',
    text: '#A5A6AD',
    border: '#1D2026'
};

const commonCartesianOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { display: false }
    },
    scales: {
        x: {
            grid: { display: false },
            ticks: { color: categoryColors.text }
        },
        y: {
            beginAtZero: true,
            grid: { color: gridColor },
            ticks: { precision: 0, color: categoryColors.text }
        }
    }
};

new Chart(document.getElementById('graficoCategorias'), {
    type: 'bar',
    data: {
        labels: categorias,
        datasets: [{
            label: 'Assets por categoria',
            data: quantidades,
            backgroundColor: categoryColors.green,
            borderRadius: 5,
            maxBarThickness: 42
        }]
    },
    options: commonCartesianOptions
});

new Chart(document.getElementById('graficoStatus'), {
    type: 'doughnut',
    data: {
        labels: ['Disponíveis', 'Indisponíveis'],
        datasets: [{
            label: 'Assets por situação',
            data: statusValores,
            backgroundColor: [categoryColors.green, categoryColors.gold],
            borderColor: categoryColors.border,
            borderWidth: 3,
            hoverOffset: 5
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '68%',
        plugins: {
            legend: {
                position: 'bottom',
                labels: { padding: 18 }
            }
        }
    }
});

new Chart(document.getElementById('graficoVendas'), {
    type: 'bar',
    data: {
        labels: vendasCategorias,
        datasets: [{
            label: 'Total vendido por categoria',
            data: vendasValores,
            backgroundColor: categoryColors.purple,
            borderRadius: 5,
            maxBarThickness: 42
        }]
    },
    options: {
        ...commonCartesianOptions,
        scales: {
            ...commonCartesianOptions.scales,
            y: {
                ...commonCartesianOptions.scales.y,
                ticks: {
                    color: categoryColors.text,
                    callback: value => `R$ ${value}`
                }
            }
        }
    }
});

new Chart(document.getElementById('graficoMeses'), {
    type: 'line',
    data: {
        labels: meses,
        datasets: [{
            label: 'Pedidos por mês',
            data: pedidosMes,
            borderColor: categoryColors.green,
            backgroundColor: 'rgba(169, 201, 135, 0.16)',
            fill: true,
            tension: 0.3,
            pointRadius: 3,
            pointHoverRadius: 5
        }]
    },
    options: {
        ...commonCartesianOptions,
        scales: {
            ...commonCartesianOptions.scales,
            y: {
                ...commonCartesianOptions.scales.y,
                ticks: { precision: 0, color: categoryColors.text }
            }
        }
    }
});