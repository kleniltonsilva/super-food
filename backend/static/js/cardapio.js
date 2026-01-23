// backend/static/js/cardapio.js

// ========== FILTRO DE CATEGORIAS ==========
document.querySelectorAll('.categoria-pill').forEach(pill => {
    pill.addEventListener('click', function() {
        // Remove active de todos
        document.querySelectorAll('.categoria-pill').forEach(p => {
            p.classList.remove('active', 'bg-primary', 'text-white');
            p.classList.add('bg-gray-200', 'text-gray-700');
        });
        // Adiciona active no clicado
        this.classList.add('active', 'bg-primary', 'text-white');
        this.classList.remove('bg-gray-200', 'text-gray-700');
        const categoriaId = this.dataset.categoria;
        filtrarProdutos(categoriaId);
    });
});

function filtrarProdutos(categoriaId) {
    const produtos = document.querySelectorAll('.produto-card');
    let visiveisCount = 0;
    produtos.forEach(produto => {
        if (categoriaId === 'todos' || produto.dataset.categoria === categoriaId) {
            produto.classList.remove('hidden');
            visiveisCount++;
        } else {
            produto.classList.add('hidden');
        }
    });
    // Mostra mensagem se não houver produtos
    document.getElementById('sem-produtos').classList.toggle('hidden', visiveisCount > 0);
}

// ========== BUSCA ==========
document.getElementById('busca-produto').addEventListener('input', function(e) {
    const termo = e.target.value.toLowerCase();
    const produtos = document.querySelectorAll('.produto-card');
    let visiveisCount = 0;
    produtos.forEach(produto => {
        const nome = produto.dataset.nome;
        if (nome.includes(termo)) {
            produto.classList.remove('hidden');
            visiveisCount++;
        } else {
            produto.classList.add('hidden');
        }
    });
    document.getElementById('sem-produtos').classList.toggle('hidden', visiveisCount > 0);
});

// ========== MODAL PRODUTO ==========
async function abrirModalProduto(produtoId) {
    const codigo = window.location.pathname.split('/')[2];
    const modal = document.getElementById('modal-produto');
    const modalContent = document.getElementById('modal-content');
    modal.classList.remove('hidden');
    modalContent.innerHTML = '<div class="p-8 text-center"><i class="fas fa-spinner fa-spin text-4xl text-primary"></i></div>';
    try {
        const response = await fetch(`/site/${codigo}/produto/${produtoId}`);
        const produto = await response.json();
        modalContent.innerHTML = `
            <div class="relative">
                <button onclick="fecharModal()" class="absolute top-4 right-4 text-gray-500 hover:text-gray-700 text-2xl z-10">
                    <i class="fas fa-times"></i>
                </button>
                ${produto.imagem_url ? `<img src="${produto.imagem_url}" class="w-full h-64 object-cover">` : ''}
                <div class="p-6">
                    <h2 class="text-2xl font-bold mb-2">${produto.nome}</h2>
                    <p class="text-gray-600 mb-4">${produto.descricao || ''}</p>
                    ${renderizarVariacoes(produto.variacoes_agrupadas)}
                    <div class="mb-4">
                        <label class="block font-semibold mb-2">Observações</label>
                        <textarea id="observacoes-produto" class="w-full border border-gray-300 rounded-lg p-2" rows="3" placeholder="Ex: Sem cebola, bem passado..."></textarea>
                    </div>
                    <div class="flex items-center justify-between mb-4">
                        <div class="flex items-center space-x-4">
                            <button onclick="alterarQuantidade(-1)" class="bg-gray-200 w-10 h-10 rounded-full hover:bg-gray-300">
                                <i class="fas fa-minus"></i>
                            </button>
                            <span id="quantidade" class="text-xl font-bold">1</span>
                            <button onclick="alterarQuantidade(1)" class="bg-gray-200 w-10 h-10 rounded-full hover:bg-gray-300">
                                <i class="fas fa-plus"></i>
                            </button>
                        </div>
                        <div class="text-right">
                            <p class="text-gray-500 text-sm">Total</p>
                            <p id="preco-total" class="text-2xl font-bold text-primary">R$ ${produto.preco_promocional || produto.preco}</p>
                        </div>
                    </div>
                    <button onclick="adicionarAoCarrinho(${produtoId})" class="w-full btn-primary text-lg">
                        <i class="fas fa-cart-plus mr-2"></i>Adicionar ao Carrinho
                    </button>
                </div>
            </div>
        `;
        // Inicializa cálculo de preço
        calcularPrecoTotal(produto);
    } catch (error) {
        console.error('Erro ao carregar produto:', error);
        modalContent.innerHTML = '<div class="p-8 text-center text-red-500">Erro ao carregar produto</div>';
    }
}

function renderizarVariacoes(variacoes) {
    if (!variacoes || Object.keys(variacoes).length === 0) return '';
    let html = '';
    for (const [tipo, opcoes] of Object.entries(variacoes)) {
        html += `
            <div class="mb-4">
                <label class="block font-semibold mb-2 capitalize">${tipo}</label>
                <div class="space-y-2">
                    ${opcoes.map((opcao, idx) => `
                        <label class="flex items-center justify-between p-3 border border-gray-300 rounded-lg cursor-pointer hover:border-primary transition">
                            <div class="flex items-center">
                                <input type="${tipo === 'tamanho' || tipo === 'ponto_carne' ? 'radio' : 'checkbox'}" name="variacao-${tipo}" value="${opcao.id}" data-preco="${opcao.preco_adicional}" ${idx === 0 && tipo === 'tamanho' ? 'checked' : ''} onchange="calcularPrecoTotal()" class="mr-3">
                                <span>${opcao.nome}</span>
                                ${opcao.descricao ? `<span class="text-sm text-gray-500 ml-2">(${opcao.descricao})</span>` : ''}
                            </div>
                            ${opcao.preco_adicional > 0 ? `<span class="text-primary font-semibold">+R$ ${opcao.preco_adicional.toFixed(2)}</span>` : ''}
                        </label>
                    `).join('')}
                </div>
            </div>
        `;
    }
    return html;
}

function calcularPrecoTotal(produto = null) {
    let precoBase = produto ? (produto.preco_promocional || produto.preco) : 0;
    // Soma variações selecionadas
    document.querySelectorAll('[name^="variacao-"]:checked').forEach(input => {
        precoBase += parseFloat(input.dataset.preco || 0);
    });
    const quantidade = parseInt(document.getElementById('quantidade').textContent);
    const total = precoBase * quantidade;
    document.getElementById('preco-total').textContent = `R$ ${total.toFixed(2)}`;
}

function alterarQuantidade(delta) {
    const qtdElement = document.getElementById('quantidade');
    let qtd = parseInt(qtdElement.textContent);
    qtd = Math.max(1, qtd + delta);
    qtdElement.textContent = qtd;
    calcularPrecoTotal();
}

async function adicionarAoCarrinho(produtoId) {
    const codigo = window.location.pathname.split('/')[2];
    const quantidade = parseInt(document.getElementById('quantidade').textContent);
    const observacoes = document.getElementById('observacoes-produto').value;
    // Coleta variações selecionadas
    const variacoesIds = [];
    document.querySelectorAll('[name^="variacao-"]:checked').forEach(input => {
        variacoesIds.push(parseInt(input.value));
    });
    try {
        const response = await fetch('/carrinho/adicionar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': getSessionId()
            },
            body: JSON.stringify({
                produto_id: produtoId,
                variacoes_ids: variacoesIds,
                quantidade: quantidade,
                observacoes: observacoes
            })
        });
        if (response.ok) {
            const data = await response.json();
            // Atualiza badge do carrinho
            atualizarBadgeCarrinho(data.quantidade_itens);
            // Feedback visual
            mostrarNotificacao('✅ Produto adicionado ao carrinho!', 'success');
            fecharModal();
        } else {
            throw new Error('Erro ao adicionar ao carrinho');
        }
    } catch (error) {
        console.error('Erro:', error);
        mostrarNotificacao('❌ Erro ao adicionar produto', 'error');
    }
}

function fecharModal() {
    document.getElementById('modal-produto').classList.add('hidden');
}

// Fecha modal ao clicar fora
document.getElementById('modal-produto').addEventListener('click', function(e) {
    if (e.target === this) {
        fecharModal();
    }
});

// ========== NOTIFICAÇÕES ==========
function mostrarNotificacao(mensagem, tipo = 'info') {
    const notif = document.createElement('div');
    notif.className = `fixed top-20 right-4 z-50 px-6 py-4 rounded-lg shadow-lg text-white ${ tipo === 'success' ? 'bg-green-500' : tipo === 'error' ? 'bg-red-500' : 'bg-blue-500' }`;
    notif.textContent = mensagem;
    document.body.appendChild(notif);
    setTimeout(() => {
        notif.remove();
    }, 3000);
}