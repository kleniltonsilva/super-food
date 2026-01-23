
// backend/static/js/carrinho.js

// ========== SESSION ID ==========
function getSessionId() {
    let sessionId = localStorage.getItem('session_id');
    if (!sessionId) {
        sessionId = 'sess_' + Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
        localStorage.setItem('session_id', sessionId);
    }
    return sessionId;
}

// ========== ATUALIZAR BADGE DO CARRINHO ==========
async function atualizarBadgeCarrinho(quantidade = null) {
    const badge = document.getElementById('carrinho-badge');
    
    if (quantidade === null) {
        // Busca quantidade do servidor
        try {
            const codigo = window.location.pathname.split('/')[2];
            const response = await fetch(`/carrinho/?codigo_acesso=${codigo}`, {
                headers: {
                    'X-Session-ID': getSessionId()
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                quantidade = data.quantidade_itens;
            }
        } catch (error) {
            console.error('Erro ao buscar carrinho:', error);
            return;
        }
    }
    
    if (quantidade > 0) {
        badge.textContent = quantidade;
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

// Inicializa badge ao carregar página
document.addEventListener('DOMContentLoaded', function() {
    atualizarBadgeCarrinho();
});
    document.getElementById('modal-produto').classList.remove('flex');