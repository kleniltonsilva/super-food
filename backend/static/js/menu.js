// backend/static/js/menu.js

// ========== MENU MOBILE ==========
document.getElementById('mobile-menu-button').addEventListener('click', function() {
    const menu = document.getElementById('mobile-menu');
    menu.classList.toggle('hidden');
});

// Fecha menu ao clicar em link
document.querySelectorAll('#mobile-menu a').forEach(link => {
    link.addEventListener('click', function() {
        document.getElementById('mobile-menu').classList.add('hidden');
    });
});
