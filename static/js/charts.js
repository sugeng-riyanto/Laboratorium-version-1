// static/js/charts.js

document.addEventListener('DOMContentLoaded', function () {
    // Ambil data dari API
    fetch('/api/analytics/data')
        .then(response => response.json())
        .then(data => {
            // Update ringkasan
            document.getElementById('total-bahan').textContent = data.bahan.total;
            document.getElementById('total-alat').textContent = data.alat.total;
            document.getElementById('expired-bahan').textContent = data.bahan.expired;
            document.getElementById('rusak-alat').textContent = data.alat.rusak;

            // === Bahan per Lab ===
            const bahanCtx = document.getElementById('bahanChart').getContext('2d');
            new Chart(bahanCtx, {
                type: 'bar',
                data: {
                    labels: data.bahan.per_lab.map(item => item.lab),
                    datasets: [{
                        label: 'Jumlah Bahan',
                        data: data.bahan.per_lab.map(item => item.count),
                        backgroundColor: '#6f42c1'
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } }
                }
            });

            // === Alat per Lab ===
            const alatCtx = document.getElementById('alatChart').getContext('2d');
            new Chart(alatCtx, {
                type: 'bar',
                data: {
                    labels: data.alat.per_lab.map(item => item.lab),
                    datasets: [{
                        label: 'Jumlah Alat',
                        data: data.alat.per_lab.map(item => item.count),
                        backgroundColor: '#28a745'
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } }
                }
            });

            // === Jadwal per Lab ===
            const jadwalCtx = document.getElementById('jadwalChart').getContext('2d');
            new Chart(jadwalCtx, {
                type: 'doughnut',
                data: {
                    labels: data.jadwal.per_lab.map(item => item.lab),
                    datasets: [{
                        data: data.jadwal.per_lab.map(item => item.count),
                        backgroundColor: ['#0d6efd', '#dc3545', '#ffc107']
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { position: 'bottom' } }
                }
            });

            // === Kejadian per Bulan ===
            const kejadianBulanCtx = document.getElementById('kejadianBulanChart').getContext('2d');
            new Chart(kejadianBulanCtx, {
                type: 'line',
                data: {
                    labels: data.kejadian.per_bulan.map(item => item.bulan),
                    datasets: [{
                        label: 'Jumlah Kejadian',
                        data: data.kejadian.per_bulan.map(item => item.count),
                        borderColor: '#dc3545',
                        backgroundColor: 'rgba(220, 53, 69, 0.1)',
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: { beginAtZero: true, ticks: { stepSize: 1 } }
                    }
                }
            });

            // === Kejadian per Lab ===
            const kejadianLabCtx = document.getElementById('kejadianLabChart').getContext('2d');
            new Chart(kejadianLabCtx, {
                type: 'bar',
                data: {
                    labels: data.kejadian.per_lab.map(item => item.lab),
                    datasets: [{
                        label: 'Jumlah Kejadian',
                        data: data.kejadian.per_lab.map(item => item.count),
                        backgroundColor: '#dc3545'
                    }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false } }
                }
            });
        })
        .catch(error => {
            console.error('Error memuat data:', error);
        });
});