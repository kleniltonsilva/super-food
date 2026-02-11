# INSTRUÇÃO PARA CLAUDE CODE — Redesign do Site Cliente React (Super Food)

## ⚠️ LEIA PRIMEIRO: Contexto do Problema

O projeto Super Food tem uma **confusão estrutural** que causou erros em atualizações anteriores. Antes de tocar em qualquer código, entenda a separação abaixo.

---

## 1. ESTRUTURA DO PROJETO — O que é código real vs. modelo de referência

### ✅ CÓDIGO REAL DO PROJETO (onde você DEVE trabalhar):

```
/home/klenilton/super-food/
├── backend/            ← API FastAPI (NÃO MEXER agora)
├── streamlit_app/      ← Painéis admin/restaurante/motoboy (NÃO MEXER agora)
├── app_motoboy/        ← App motoboy (NÃO MEXER agora)
├── db/                 ← Banco de dados (NÃO MEXER agora)
├── main.py             ← Entry point
├── start_services.sh   ← Script que inicia tudo
└── ... (outros arquivos raiz)
```

O **Site Cliente** (porta 8504) funciona assim:

- **Streamlit** inicia o site: `streamlit run streamlit_app/cliente_app.py --server.port=8504`
- **React** (build opcional) está em: `restaurante-pedido-online/` → gera `restaurante-pedido-online/dist/`
- O Streamlit (`streamlit_app/cliente_app.py`) serve o build React (`dist/`) quando disponível

Portanto os dois arquivos/pastas relevantes são:
1. `streamlit_app/cliente_app.py` ← Arquivo Streamlit que serve o site (ENTRADA PRINCIPAL)
2. `restaurante-pedido-online/` ← Código React (src/, components/, etc.) que gera o `dist/`

**Ambos precisam ser trabalhados:** o React para o visual/componentes, e o `cliente_app.py` para garantir que serve corretamente.

### ❌ MODELOS DE REFERÊNCIA (NUNCA modifique estes arquivos):

```
/home/klenilton/super-food/restaurante-pedido-online/
├── MODELOS DE RESTAURANTES/     ← Sites modelo baixados da internet (SÓ REFERÊNCIA VISUAL)
│   ├── restaurante-modelo/      ← Modelo tipo marmitex/restaurante delivery
│   ├── pizzaria/                ← Modelo tipo pizzaria
│   ├── acai-e-sorvete/          ← Modelo tipo açaí e sorveteria
│   └── (outras categorias que existirem na pasta)/
│   │
│   │   Cada pasta contém:
│   │   ├── *.html               ← Arquivo HTML do site modelo (abrir no navegador para ver o layout)
│   │   └── (imagens, css, js)   ← Assets visuais do modelo
├── client/                      ← ⚠️ CUIDADO: pode ter código antigo/confuso aqui
├── components.json
├── package.json
├── todo.md
├── tsconfig.json
└── vite.config.ts
```

**ATENÇÃO:** A pasta `restaurante-pedido-online/client/` e os arquivos `package.json`, `vite.config.ts` etc. na raiz de `restaurante-pedido-online/` foram erroneamente modificados em atualizações anteriores. **NÃO são o site ativo da porta 8504** (ou podem ser — confirme via `start_services.sh`).

---

## 2. O QUE FAZER — Passo a passo obrigatório

### PASSO 0 — Diagnóstico (OBRIGATÓRIO antes de qualquer código)

1. **Leia o `claude.md`** na raiz do projeto (se existir)
2. **Estrutura já identificada:**
   - `start_services.sh` inicia o site cliente com: `streamlit run streamlit_app/cliente_app.py --server.port=8504`
   - O React está em: `restaurante-pedido-online/` (REACT_DIR) → build gera `restaurante-pedido-online/dist/`
   - O Streamlit (`streamlit_app/cliente_app.py`) serve o build React quando `dist/` existe
3. **Leia o `streamlit_app/cliente_app.py`** para entender como ele serve o React e integra com a API
4. **Leia a estrutura React em `restaurante-pedido-online/src/`** para mapear os componentes atuais
5. **Abra os arquivos HTML dos modelos** em `restaurante-pedido-online/MODELOS DE RESTAURANTES/` para entender o layout visual de referência

**Mapa confirmado:**
| O quê | Pasta |
|-------|-------|
| Site ativo (Streamlit, porta 8504) | `streamlit_app/cliente_app.py` |
| Código React (build → dist/) | `restaurante-pedido-online/src/` |
| Modelos de referência visual | `restaurante-pedido-online/MODELOS DE RESTAURANTES/` |

### PASSO 1 — Análise dos Modelos de Referência

Abra e analise os arquivos HTML dentro de **todas as subpastas** de:
```
/home/klenilton/super-food/restaurante-pedido-online/MODELOS DE RESTAURANTES/
```
Cada subpasta (restaurante-modelo, pizzaria, acai-e-sorvete, etc.) representa um tipo/categoria de restaurante com seu layout próprio.

Extraia deles:
- Estrutura do layout (header, seções de categorias, grid de produtos, footer)
- Estilo visual (cores, tipografia, espaçamentos, botões, cards de produto)
- Componentes visuais (barra de busca, carrinho, login, banner, categorias como seções na página)
- Como os produtos são exibidos (cards compactos, carrossel, grade)

### PASSO 2 — Redesign dos Componentes React

Aplique o visual dos modelos **apenas no código React ativo (porta 8504)**, mantendo:

- ✅ Toda a lógica de negócio existente (hooks, chamadas à API FastAPI, estado)
- ✅ Integração com o banco de dados do projeto
- ✅ Integração com o painel do restaurante (dados dinâmicos: produtos, categorias, cores do tema, horários)
- ✅ Funcionalidade do carrinho, pedidos, etc.
- ❌ NÃO altere o backend/API
- ❌ NÃO altere os painéis Streamlit
- ❌ NÃO modifique nada dentro de `restaurante-pedido-online/MODELOS DE RESTAURANTES/`

O redesign deve focar em:
1. **Home.tsx** (ou equivalente) — layout dinâmico por tipo de restaurante:
   - Quando o restaurante é tipo "restaurante/marmitex" → usar visual do modelo `restaurante-modelo/`
   - Quando o restaurante é tipo "pizzaria" → usar visual do modelo `pizzaria/`
   - Quando o restaurante é tipo "açaí/sorvete" → usar visual do modelo `acai-e-sorvete/`
   - E assim por diante para cada tipo que existir na pasta de modelos
   - A lógica de qual modelo visual aplicar deve vir do tipo/categoria do restaurante cadastrado no banco
   - Todas as categorias aparecem como seções na página (scroll vertical)
   - Produtos em grid/carrossel dentro de cada seção
   - Header profissional com logo do restaurante, busca, login
   - Cards de produto compactos e bonitos
2. **Componentes auxiliares** que precisem de ajuste visual
3. **CSS/Tailwind** para replicar o estilo dos modelos

### PASSO 3 — Validação

Depois de implementar:
1. Inicie o serviço: `./start_services.sh`
2. Acesse: `http://localhost:8504/?restaurante=6F31B76C`
3. Confirme que:
   - O layout visual está parecido com os modelos de referência
   - Os dados vêm do banco de dados (produtos, categorias, nome do restaurante)
   - O carrinho funciona
   - Os pedidos funcionam
   - Nenhum JSON aparece para o cliente final

---

## 3. REGRAS IMPORTANTES

1. **Envie sempre o código completo de cada arquivo modificado** — para eu copiar e colar substituindo o anterior
2. **Nunca modifique arquivos dentro de `MODELOS DE RESTAURANTES/`** — são apenas referência visual
3. **Se encontrar inconsistência** entre o que está na pasta de modelos e o site ativo, **me informe antes de agir**
4. **Use o banco de dados e API existentes** — não crie endpoints novos sem necessidade
5. **Mantenha `.env`** para qualquer configuração sensível
6. **Código limpo, comentado, profissional**

---

## 4. RESUMO DA TAREFA

| Item | Detalhe |
|------|---------|
| **Objetivo** | Redesenhar o visual do site cliente React para parecer com os modelos "Expresso Delivery" |
| **Site ativo** | Streamlit: `streamlit_app/cliente_app.py` (porta 8504) + React: `restaurante-pedido-online/src/` (build → `dist/`) |
| **Modelos visuais** | `restaurante-pedido-online/MODELOS DE RESTAURANTES/` (todas as subpastas: restaurante-modelo, pizzaria, acai-e-sorvete, etc.) |
| **Manter** | Lógica de negócio, hooks, API, banco de dados, integração com painel restaurante |
| **Não tocar** | Backend, Streamlit, banco de dados, arquivos dos modelos |
| **Resultado esperado** | Site com layout visual específico por tipo de restaurante (baseado nos modelos), 100% funcional com dados reais |
