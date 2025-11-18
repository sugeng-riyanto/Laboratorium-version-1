// static/js/mobile.js

document.addEventListener('DOMContentLoaded', function () {
    // 1. Auto-hide alert setelah 60 detik (sudah ada, tapi pastikan ID konsisten)
    const loginAlert = document.getElementById('loginAlert');
    if (loginAlert) {
        setTimeout(() => {
            loginAlert.style.display = 'none';
        }, 60000);
    }

    // 2. Pastikan dropdown navbar tertutup saat diklik di mobile
    const navbarToggles = document.querySelectorAll('.navbar-toggler');
    const navLinks = document.querySelectorAll('.nav-link, .dropdown-item');

    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            const navbarCollapse = document.querySelector('.navbar-collapse');
            if (navbarCollapse.classList.contains('show')) {
                const bsCollapse = bootstrap.Collapse.getInstance(navbarCollapse);
                if (bsCollapse) bsCollapse.hide();
            }
        });
    });

    // 3. (Opsional) Tambahkan swipe untuk navigasi minggu di mobile
    // (Dibutuhkan library tambahan seperti Hammer.js — skip untuk sederhana)
});