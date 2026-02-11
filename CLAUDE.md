# CLAUDE.md — Memória Técnica Viva do Super Food

---

## ⚙️ REGRAS PERMANENTES PARA O CLAUDE CODE

1. **SEMPRE** que modificar, criar ou deletar qualquer arquivo do projeto, **ATUALIZE este CLAUDE.md** antes de encerrar a resposta.
2. Atualize: plano de execução, última sessão, roadmap, problemas e qualquer seção técnica afetada.
3. **SEMPRE** crie um **PLANO DE EXECUÇÃO** antes de implementar qualquer coisa.
4. **SEMPRE** atualize os checkpoints do plano conforme avança cada etapa.
5. Se a sessão for interrompida, o plano deve mostrar exatamente onde parou.
6. Estas regras são **PERMANENTES** e se aplicam a **TODOS** os comandos.
7. Responder **sempre em português**.
8. Gerar **código completo**, nunca snippets parciais.
9. **NUNCA** armazenar objetos ORM no `session_state`.
10. **TODAS** as queries devem filtrar por `restaurante_id` (multi-tenant).
11. No React, usar hooks de `hooks/useQueries.ts` — **NUNCA** useState+useEffect manual para fetching.
12. Senhas **SEMPRE** com `.strip()` antes de hash.
13. Interceptor 401 já existe no `apiClient.ts` — não duplicar.

---

## 🔨 PLANO DE EXECUÇÃO ATUAL

- **Tarefa:** Documentação completa do projeto (CLAUDE.md, README.md, ESTRUTURA.md)
- **Status:** ✅ Concluída
- **Início:** 10/02/2026

Etapas:
1. [x] Analisar todos os models, schemas, routers, pages e utils ✅
   - Arquivos envolvidos: todo o projeto
   - Resultado: 28 models, 50+ endpoints, 11 pages React, 4 apps Streamlit catalogados
2. [x] Criar CLAUDE.md completo ✅
3. [x] Criar README.md atualizado ✅
4. [x] Criar ESTRUTURA.md com árvore e fluxos ✅

---

## 🕐 ÚLTIMA SESSÃO

- **Data:** 10/02/2026
- **O que foi feito:** Documentação completa do projeto (3 arquivos)
- **Arquivos criados:** `ESTRUTURA.md` (arvore completa + 7 fluxos de dados)
- **Arquivos modificados:** `CLAUDE.md` (783 linhas), `README.md` (475 linhas)
- **Arquivos deletados:** nenhum
- **Migration criada:** não
- **Plano concluído:** sim
- **Problemas encontrados:** nenhum

### Sessão anterior (08/02/2026)
- React SPA completo: todas as pages adaptadas para apiClient
- RestauranteContext + AuthContext + useQueries.ts criados
- auth_cliente.py: registro, login, /me, perfil, endereços CRUD
- carrinho.py: geocodifica endereço, calcula taxa real
- Home.tsx: emoji/tema dinâmico, banner, rodapé
- Account.tsx: nova página Minha Conta
- Upload router: processamento de imagens com Pillow
- Plano etapa 7 concluída (apiClient.ts), próximo: etapa 8+

---

## 🗺️ ROADMAP

1. ✅ Fase 1: Sistema base com ORM SQLAlchemy
2. ✅ Fase 2: Migração completa para Alembic
3. ✅ Fase 3: Site do Cliente (4ª cabeça - Streamlit)
4. ✅ Fase 4: Seleção justa de motoboys
5. ✅ Fase 5: Cálculo automático de taxas e ganhos
6. ✅ Fase 6: Backend FastAPI com Site Cliente
7. ✅ Fase 7: Isolamento multi-tenant de motoboys (v2.8.0)
8. ✅ Fase 8: GPS em tempo real + Mapa no restaurante (v2.8.1)
9. ✅ Fase 9: Site Cliente React SPA (v3.0) — Sprint 1-3 concluídos
10. ⬚ Fase 10: Finalizar Sprint 2 React (etapas 8-18 do plano)
11. ⬚ Fase 11: Integração iFood
12. ⬚ Fase 12: App nativo (WebView)
13. ⬚ Fase 13: Recuperação de senha por SMS (Twilio/AWS SNS)
14. ⬚ Fase 14: Push notifications para motoboy (PWA)

### Plano de Integração React (Sprint 2 — Etapas pendentes)
- Etapa 8: [ ] Criar/Adaptar RestauranteContext.tsx (já feito parcialmente)
- Etapa 9: [ ] Adaptar main.tsx e App.tsx (já feito parcialmente)
- Etapa 10-18: [ ] Adaptar páginas restantes para usar apiClient completo

---

## ⚠️ PROBLEMAS PENDENTES

- [ ] `plano.txt` e `reparar_bugs.txt` foram deletados do working tree (existem no git HEAD)
- [ ] Arquivo `001_initial_schema,` (vazio) e `=10.0.0` na raiz — lixo para limpar
- [ ] `.env` com segredos commitado no git — mover para `.gitignore`
- [ ] `carrinho.py:452` usa `longitude=lng_entrega` — campo correto é `longitude_entrega`
- [ ] GPS router (`gps.py`) não requer autenticação — considerar proteção
- [ ] Upload router (`upload.py`) não requer autenticação — considerar proteção
- [ ] `restaurantes.py` usa campos `hashed_password`, `lat`, `lon` que não existem no model atual
- [ ] `pedidos.py` usa `nome_cliente`, `endereco`, `StatusPedido` que não existem no model atual
- [x] Fechamento de caixa: valor contado + cálculo diferença (corrigido 07/02/2026)
- [x] Pagamentos motoboy: exportação CSV funcional (corrigido 07/02/2026)

---

## 📋 PROJETO

**Super Food** — SaaS multi-tenant para gestão de restaurantes com despacho inteligente de entregas.

- **Versão:** 2.8.3+ (10/02/2026)
- **Licença:** Proprietária (Klenilton Silva)

---

## 🏗️ ARQUITETURA

### Stack

| Camada | Tecnologia | Versão |
|--------|-----------|--------|
| Backend API | FastAPI + Uvicorn | 0.115+ |
| ORM | SQLAlchemy 2.0+ | 2.0.25+ |
| Migrations | Alembic | 1.13+ |
| Banco (dev) | SQLite | nativo |
| Banco (prod) | PostgreSQL | via psycopg2 |
| Dashboard Admin | Streamlit | 1.40+ |
| Dashboard Restaurante | Streamlit | 1.40+ |
| App Motoboy (PWA) | Streamlit | 1.40+ |
| Site Cliente (novo) | React 19 + Vite 7 | 19.2+ |
| Estado React | TanStack Query v5 | 5.90+ |
| Router React | wouter | 3.3+ |
| CSS React | Tailwind CSS 4 + Radix UI | 4.1+ |
| Auth | JWT (python-jose) + bcrypt | HS256 |
| Mapas | Mapbox API | — |
| Imagens | Pillow (resize/WebP) | 10.0+ |

### Serviços e Portas

| Serviço | Porta | Arquivo | Comando |
|---------|-------|---------|---------|
| FastAPI Backend | 8000 | `backend/app/main.py` | `uvicorn backend.app.main:app --port 8000 --reload` |
| Super Admin | 8501 | `streamlit_app/super_admin.py` | `streamlit run streamlit_app/super_admin.py --server.port 8501` |
| Dashboard Restaurante | 8502 | `streamlit_app/restaurante_app.py` | `streamlit run streamlit_app/restaurante_app.py --server.port 8502` |
| App Motoboy PWA | 8503 | `app_motoboy/motoboy_app.py` | `streamlit run app_motoboy/motoboy_app.py --server.port 8503` |
| React SPA (dev) | 5173 | `restaurante-pedido-online/` | `cd restaurante-pedido-online && npm run dev` |
| React SPA (prod) | 8000 | Servido pelo FastAPI | `GET /cliente/{codigo_acesso}` |

### Como as partes se conectam

```
[React SPA]  ──HTTP──►  [FastAPI :8000]  ──ORM──►  [SQLite/PostgreSQL]
                              │
[Streamlit Admin :8501] ──ORM──┤
[Streamlit Rest. :8502] ──ORM──┤
[App Motoboy :8503] ──ORM+GPS──┘
                              │
                         [WebSocket /ws/{id}]  ──►  Tempo real
```

- React SPA: consome API FastAPI via `apiClient.ts` (proxy Vite em dev, servido pelo FastAPI em prod)
- Streamlit apps: acessam banco diretamente via `get_db_session()` (database/session.py)
- WebSocket: notificações em tempo real por restaurante
- GPS: motoboy envia a cada 10s via `POST /api/gps/update`

---

## 🗄️ BANCO DE DADOS

- **Arquivo dev:** `super_food.db` (raiz do projeto)
- **ORM principal:** `database/models.py` (28 classes)
- **Sessão Streamlit:** `database/session.py` → `get_db_session()` (retorno direto, fechar manualmente)
- **Sessão FastAPI:** `backend/app/database.py` → `get_db()` (generator para DI)
- **Base ORM:** `database/base.py`

### Comandos Alembic
```bash
alembic upgrade head        # Aplicar todas as migrations
alembic downgrade -1        # Reverter última
alembic current             # Ver versão atual
alembic history             # Ver histórico
alembic revision --autogenerate -m "descricao"  # Nova migration
```

### Migrations (12 total)
| # | Arquivo | Descrição |
|---|---------|-----------|
| 1 | `001_initial_schema.py` | Tabelas core (super_admin, restaurantes, motoboys, pedidos, etc) |
| 2 | `002_add_gps_motoboys_table.py` | Tabela GPS para motoboys |
| 3 | `003_add_site_cliente_schema.py` | site_config, categorias, produtos, variações, clientes, carrinho |
| 4 | `004_add_motoboy_selection_fields.py` | Campos de seleção justa (hierarquia, disponível, em_rota) |
| 5 | `005_add_motoboy_usuario_unique_constraint.py` | Unique (restaurante_id, usuario) |
| 6 | `006_add_modo_prioridade_e_motivo_finalizacao.py` | Modo de despacho + motivo finalização |
| 7 | `c6876da_add_site_cliente_tables_fidelidade.py` | Fidelidade, prêmios, promoções |
| 8 | `d494f82_add_pagamento_real_fields.py` | Pagamento real (dinheiro vs cartão) |
| 9 | `b7b9e66_add_ranking_antifraude_fields.py` | Antifraude + CPF |
| 10 | `007_add_missing_columns.py` | Campos endereço restaurante + pagamento motoboy |
| 11 | `008_add_combos.py` | Tabelas de combos promocionais |
| 12 | `009_add_max_sabores.py` | max_sabores por variação |

---

## 📦 MODELOS (database/models.py) — 28 Classes

### SuperAdmin
**Tabela:** `super_admin`
| Campo | Tipo | Obrigatório | Unique | Default |
|-------|------|-------------|--------|---------|
| id | Integer PK | sim | sim | auto |
| usuario | String(50) | sim | sim | — |
| senha_hash | String(256) | sim | não | — |
| email | String(100) | não | sim | — |
| ativo | Boolean | não | não | True |
| criado_em | DateTime | não | não | utcnow |
**Métodos:** `set_senha(senha)`, `verificar_senha(senha)` — SHA256 com strip()

### Restaurante
**Tabela:** `restaurantes`
| Campo | Tipo | Obrigatório | Unique | Default |
|-------|------|-------------|--------|---------|
| id | Integer PK | sim | sim | auto |
| nome | String(200) | sim | não | — |
| nome_fantasia | String(200) | sim | não | — |
| razao_social | String(200) | não | não | — |
| cnpj | String(14) | não | sim | — |
| email | String(100) | sim | sim | — |
| senha | String(256) | sim | não | — |
| telefone | String(20) | sim | não | — |
| endereco_completo | Text | sim | não | — |
| cidade | String(100) | não | não | — |
| estado | String(2) | não | não | — |
| cep | String(10) | não | não | — |
| latitude | Float | não | não | — |
| longitude | Float | não | não | — |
| plano | String(50) | sim | não | 'basico' |
| valor_plano | Float | sim | não | 0.0 |
| limite_motoboys | Integer | sim | não | 3 |
| codigo_acesso | String(20) | sim | sim | — |
| ativo | Boolean | não | não | True |
| status | String(20) | não | não | 'ativo' |
| criado_em | DateTime | não | não | utcnow |
| data_vencimento | DateTime | não | não | — |
**Relacionamentos:** config (1:1), site_config (1:1), motoboys (1:N), pedidos (1:N), produtos (1:N), categorias_menu (1:N), clientes (1:N), carrinhos (1:N), caixas (1:N), notificacoes (1:N), solicitacoes_motoboy (1:N), rotas_otimizadas (1:N), combos (1:N)
**Métodos:** `gerar_codigo_acesso()`, `set_senha(senha)`, `verificar_senha(senha)`

### SiteConfig
**Tabela:** `site_config` — Configuração visual/operacional do site por restaurante
| Campo | Tipo | Default |
|-------|------|---------|
| id | Integer PK | auto |
| restaurante_id | Integer FK (unique) | — |
| tipo_restaurante | String(50) | 'geral' |
| tema_cor_primaria | String(7) | '#FF6B35' |
| tema_cor_secundaria | String(7) | '#004E89' |
| logo_url, banner_principal_url, favicon_url | String(500) | null |
| whatsapp_numero | String(20) | null |
| whatsapp_ativo | Boolean | True |
| whatsapp_mensagem_padrao | Text | 'Olá! Gostaria de fazer um pedido.' |
| pedido_minimo | Float | 0.0 |
| tempo_entrega_estimado | Integer | 50 |
| tempo_retirada_estimado | Integer | 20 |
| site_ativo | Boolean | True |
| aceita_agendamento | Boolean | False |
| aceita_dinheiro, aceita_cartao, aceita_pix | Boolean | True |
| aceita_vale_refeicao | Boolean | False |
| meta_title, meta_description, meta_keywords | Text | null |

### ConfigRestaurante
**Tabela:** `config_restaurante` — Configurações operacionais
| Campo | Tipo | Default |
|-------|------|---------|
| id | Integer PK | auto |
| restaurante_id | Integer FK (unique) | — |
| status_atual | String(20) | 'fechado' |
| modo_despacho | String(50) | 'auto_economico' |
| raio_entrega_km | Float | 10.0 |
| tempo_medio_preparo | Integer | 30 |
| despacho_automatico | Boolean | True |
| modo_prioridade_entrega | String(50) | 'rapido_economico' |
| taxa_entrega_base | Float | 5.0 |
| distancia_base_km | Float | 3.0 |
| taxa_km_extra | Float | 1.5 |
| valor_km | Float | 2.0 |
| valor_base_motoboy | Float | 5.0 |
| valor_km_extra_motoboy | Float | 1.0 |
| taxa_diaria | Float | 0.0 |
| valor_lanche | Float | 0.0 |
| max_pedidos_por_rota | Integer | 5 |
| permitir_ver_saldo_motoboy | Boolean | True |
| permitir_finalizar_fora_raio | Boolean | False |
| distancia_base_motoboy_km | Float | 3.0 |
| horario_abertura | String(5) | '18:00' |
| horario_fechamento | String(5) | '23:00' |
| dias_semana_abertos | String(200) | 'segunda,...,domingo' |

### CategoriaMenu
**Tabela:** `categorias_menu`
Campos: id, restaurante_id (FK), nome, descricao, icone, imagem_url, ordem_exibicao, ativo, criado_em

### TipoProduto
**Tabela:** `tipos_produto` — Templates por tipo de restaurante
Campos: id, tipo_restaurante, nome_template, descricao, config_json (JSON), ativo

### Produto
**Tabela:** `produtos`
Campos: id, restaurante_id (FK), categoria_id (FK), tipo_produto_id (FK), nome, descricao, preco, imagem_url, imagens_adicionais_json (JSON), destaque, promocao, preco_promocional, ordem_exibicao, estoque_ilimitado, estoque_quantidade, disponivel, criado_em
**Relacionamentos:** categoria, tipo_produto, variacoes (1:N), itens_pedido (1:N)

### VariacaoProduto
**Tabela:** `variacoes_produto`
Campos: id, produto_id (FK), tipo_variacao (tamanho/sabor/borda/adicional/ponto_carne), nome, descricao, preco_adicional, ordem, ativo, estoque_disponivel, max_sabores

### Cliente
**Tabela:** `clientes`
Campos: id, restaurante_id (FK), nome, email (unique), telefone, senha_hash, cpf, data_nascimento (Date), ativo, email_verificado, telefone_verificado, data_cadastro, ultimo_acesso
**Métodos:** `set_senha()`, `verificar_senha()` — SHA256 com strip()
**Relacionamentos:** enderecos (1:N), pedidos (1:N), carrinhos (1:N)

### EnderecoCliente
**Tabela:** `enderecos_cliente`
Campos: id, cliente_id (FK), apelido, cep, endereco_completo, numero, complemento, bairro, cidade, estado, referencia, latitude, longitude, validado_mapbox, padrao, ativo, criado_em

### Carrinho
**Tabela:** `carrinho`
Campos: id, restaurante_id (FK), cliente_id (FK nullable), sessao_id, itens_json (JSON), valor_subtotal, valor_taxa_entrega, valor_desconto, valor_total, cupom_codigo, data_criacao, data_atualizacao, data_expiracao

### Pedido
**Tabela:** `pedidos`
Campos: id, restaurante_id (FK), cliente_id (FK nullable), comanda, tipo, origem ('manual'|'site'), tipo_entrega, cliente_nome, cliente_telefone, endereco_entrega, latitude_entrega, longitude_entrega, numero_mesa, itens (Text), carrinho_json (JSON), observacoes, valor_total, forma_pagamento, troco_para, forma_pagamento_real, valor_pago_dinheiro, valor_pago_cartao, cupom_desconto, valor_desconto, distancia_restaurante_km, ordem_rota, validado_mapbox, atrasado, agendado, data_agendamento, status, tempo_estimado, despachado, data_criacao, atualizado_em
**Relacionamentos:** itens_detalhados (1:N ItemPedido), entrega (1:1)

### ItemPedido
**Tabela:** `itens_pedido`
Campos: id, pedido_id (FK), produto_id (FK), quantidade, preco_unitario, observacoes

### Entrega
**Tabela:** `entregas`
Campos: id, pedido_id (FK unique), motoboy_id (FK), distancia_km, tempo_entrega, posicao_rota_original, posicao_rota_otimizada, tempo_preparacao, valor_entrega, taxa_base, taxa_km_extra, valor_motoboy, valor_base_motoboy, valor_extra_motoboy, valor_lanche, valor_diaria, delivery_started_at, delivery_finished_at, finalizado_fora_raio, status, motivo_finalizacao, motivo_cancelamento, atribuido_em, entregue_em

### Motoboy
**Tabela:** `motoboys`
Campos: id, restaurante_id (FK), nome, usuario, telefone, senha, status (pendente/ativo/inativo/excluido), capacidade_entregas, ultimo_status_online, cpf, latitude_atual, longitude_atual, ultima_atualizacao_gps, total_entregas, total_ganhos, total_km, ordem_hierarquia, disponivel, em_rota, entregas_pendentes, ultima_entrega_em, ultima_rota_em, data_cadastro, data_solicitacao, data_exclusao
**Métodos:** `set_senha()`, `verificar_senha()` — SHA256 com strip()
**Índices:** idx_motoboy_restaurante, idx_motoboy_usuario, idx_motoboy_disponivel, idx_motoboy_hierarquia

### MotoboySolicitacao
**Tabela:** `motoboys_solicitacoes`
Campos: id, restaurante_id (FK), nome, usuario, telefone, codigo_acesso, data_solicitacao, status

### RotaOtimizada
**Tabela:** `rotas_otimizadas`
Campos: id, restaurante_id (FK), motoboy_id (FK), total_pedidos, distancia_total_km, tempo_total_min, ordem_entregas (JSON), status, data_criacao, data_inicio, data_conclusao

### Caixa
**Tabela:** `caixa`
Campos: id, restaurante_id (FK), data_abertura, operador_abertura, valor_abertura, total_vendas, valor_retiradas, status, data_fechamento, operador_fechamento, valor_contado, diferenca

### MovimentacaoCaixa
**Tabela:** `movimentacoes_caixa`
Campos: id, caixa_id (FK), tipo, valor, descricao, data_hora

### Notificacao
**Tabela:** `notificacoes`
Campos: id, restaurante_id (FK), motoboy_id (FK), tipo, titulo, mensagem, lida, data_criacao

### GPSMotoboy
**Tabela:** `gps_motoboys`
Campos: id, motoboy_id (FK), restaurante_id (FK), latitude, longitude, velocidade, timestamp

### BairroEntrega
**Tabela:** `bairros_entrega`
Campos: id, restaurante_id (FK), nome, taxa_entrega, tempo_estimado_min, ativo, criado_em, atualizado_em

### PontosFidelidade
**Tabela:** `pontos_fidelidade`
Campos: id, cliente_id (FK unique), restaurante_id (FK), pontos_total, pontos_disponiveis

### TransacaoFidelidade
**Tabela:** `transacoes_fidelidade`
Campos: id, cliente_id (FK), restaurante_id (FK), pedido_id (FK), tipo ('ganho'|'resgatado'), pontos, descricao, criado_em

### PremioFidelidade
**Tabela:** `premios_fidelidade`
Campos: id, restaurante_id (FK), nome, descricao, custo_pontos, tipo_premio ('desconto'|'item_gratis'|'brinde'), valor_premio, ordem_exibicao, ativo

### Promocao
**Tabela:** `promocoes`
Campos: id, restaurante_id (FK), nome, descricao, tipo_desconto ('percentual'|'fixo'), valor_desconto, valor_pedido_minimo, desconto_maximo, codigo_cupom, data_inicio, data_fim, uso_limitado, limite_usos, usos_realizados, ativo

### Combo
**Tabela:** `combos`
Campos: id, restaurante_id (FK), nome, descricao, preco_combo, preco_original, imagem_url, ativo, ordem_exibicao, data_inicio, data_fim
**Relacionamentos:** itens (1:N ComboItem)

### ComboItem
**Tabela:** `combo_itens`
Campos: id, combo_id (FK), produto_id (FK), quantidade

---

## 📄 SCHEMAS (backend/app/schemas/)

### schemas/__init__.py (legado — rotas de restaurante)
- `RestauranteBase` → `RestauranteCreate` → `RestaurantePublic`
- `PedidoBase` → `PedidoCreate` → `PedidoPublic`

### cliente_schemas.py
| Schema | Campos obrigatórios | Uso |
|--------|---------------------|-----|
| ClienteCadastroRequest | nome, email, telefone, senha, codigo_acesso_restaurante | POST /auth/cliente/registro |
| ClienteLoginRequest | email, senha, codigo_acesso_restaurante | POST /auth/cliente/login |
| ClienteResponse | id, nome, email, telefone | Resposta de perfil |
| TokenResponse | access_token, token_type, cliente | Resposta de auth |
| RegistroPosPedidoRequest | nome, email, telefone, senha, codigo_acesso_restaurante, pedido_id? | POST registro-pos-pedido |
| ClientePerfilUpdate | nome?, telefone?, cpf?, data_nascimento? | PUT /auth/cliente/perfil |
| EnderecoCreateRequest | endereco_completo (obrig), demais opcionais | POST /auth/cliente/enderecos |
| EnderecoUpdateRequest | todos opcionais | PUT /auth/cliente/enderecos/{id} |
| EnderecoResponse | id + todos campos endereço | Resposta de endereço |
| PedidoClienteResponse | id, comanda, status, tipo, valor_total, data_criacao | Resposta de pedido |

### site_schemas.py
| Schema | Uso |
|--------|-----|
| SiteInfoPublic | GET /site/{codigo} — info completa do restaurante |
| CategoriaPublic | GET /site/{codigo}/categorias |
| VariacaoSimples | Variação dentro de ProdutoPublic |
| ProdutoPublic | GET /site/{codigo}/produtos |
| ProdutoDetalhadoPublic | GET /site/{codigo}/produto/{id} — com variacoes_agrupadas |
| ValidacaoEntregaRequest/Response | POST /site/{codigo}/validar-entrega |
| BairroEntregaPublic | GET /site/{codigo}/bairros |
| PontosFidelidadePublic | GET fidelidade/pontos |
| PremioFidelidadePublic | GET fidelidade/premios |
| ResgatePremioRequest/Response | POST fidelidade/resgatar |
| PromocaoPublic | GET /site/{codigo}/promocoes |
| ValidarCupomRequest/Response | POST /site/{codigo}/validar-cupom |
| ComboItemPublic / ComboPublic | GET /site/{codigo}/combos |

### carrinho_schemas.py
| Schema | Uso |
|--------|-----|
| AdicionarItemRequest | POST /carrinho/adicionar — produto_id, variacoes_ids[], quantidade, observacoes |
| CarrinhoResponse | Resposta padrão — id, sessao_id, itens[], totais |
| FinalizarCarrinhoRequest | POST /carrinho/finalizar — tipo_entrega, forma_pagamento, endereço, cliente |

---

## 🌐 ROTAS (backend/app/routers/) — 50+ Endpoints

### restaurantes.py — Prefixo: `/restaurantes`
| Método | Path | Auth | Descrição |
|--------|------|------|-----------|
| POST | /restaurantes/signup | Público | Cria restaurante (geocodifica endereço) |
| GET | /restaurantes/ | Público | Lista restaurantes |
| GET | /restaurantes/{id} | Público | Detalhe do restaurante |

### auth_cliente.py — Prefixo: `/auth/cliente`
| Método | Path | Auth | Descrição |
|--------|------|------|-----------|
| POST | /auth/cliente/registro | Público | Cadastro de cliente (bcrypt, JWT 72h) |
| POST | /auth/cliente/login | Público | Login do cliente |
| POST | /auth/cliente/registro-pos-pedido | Público | Registro após pedido anônimo |
| GET | /auth/cliente/me | Token | Retorna dados do cliente logado |
| PUT | /auth/cliente/perfil | Token | Atualiza perfil |
| GET | /auth/cliente/enderecos | Token | Lista endereços |
| POST | /auth/cliente/enderecos | Token | Cria endereço |
| PUT | /auth/cliente/enderecos/{id} | Token | Atualiza endereço |
| DELETE | /auth/cliente/enderecos/{id} | Token | Remove endereço (soft delete) |
| PUT | /auth/cliente/enderecos/{id}/padrao | Token | Define endereço padrão |
| GET | /auth/cliente/pedidos | Token | Lista pedidos do cliente (últimos 50) |
| GET | /auth/cliente/pedidos/{id} | Token | Detalhe do pedido |

### site_cliente.py — Prefixo: `/site`
| Método | Path | Auth | Descrição |
|--------|------|------|-----------|
| GET | /site/{codigo} | Público | Info pública do restaurante (SiteInfoPublic) |
| GET | /site/{codigo}/categorias | Público | Categorias do menu |
| GET | /site/{codigo}/produtos | Público | Produtos com filtros (?categoria_id, ?destaque, ?promocao, ?busca) |
| GET | /site/{codigo}/produto/{id} | Público | Produto detalhado com variações agrupadas |
| POST | /site/{codigo}/validar-entrega | Público | Valida endereço + calcula taxa |
| GET | /site/{codigo}/autocomplete-endereco | Público | Autocomplete Mapbox (?query) |
| GET | /site/{codigo}/bairros | Público | Bairros atendidos |
| GET | /site/{codigo}/bairro/{nome} | Público | Busca bairro por nome |
| GET | /site/{codigo}/produto/{id}/sabores | Público | Sabores da mesma categoria |
| GET | /site/{codigo}/combos | Público | Combos ativos |
| GET | /site/{codigo}/pedido/{id}/tracking | Público | Tracking do pedido + GPS motoboy |
| GET | /site/{codigo}/fidelidade/pontos/{cliente_id} | Público | Saldo de pontos |
| GET | /site/{codigo}/fidelidade/premios | Público | Prêmios disponíveis |
| POST | /site/{codigo}/fidelidade/resgatar/{cliente_id} | Público | Resgata prêmio |
| GET | /site/{codigo}/promocoes | Público | Promoções ativas |
| POST | /site/{codigo}/validar-cupom | Público | Valida cupom de desconto |

### carrinho.py — Prefixo: `/carrinho`
| Método | Path | Auth | Descrição |
|--------|------|------|-----------|
| POST | /carrinho/adicionar | Sessão (X-Session-ID) | Adiciona item ao carrinho |
| POST | /carrinho/adicionar-combo | Sessão | Adiciona combo inteiro |
| GET | /carrinho/ | Sessão | Busca carrinho (?codigo_acesso) |
| PUT | /carrinho/atualizar-quantidade/{index} | Sessão | Atualiza quantidade (?nova_quantidade) |
| DELETE | /carrinho/remover/{index} | Sessão | Remove item |
| DELETE | /carrinho/limpar | Sessão | Limpa carrinho |
| POST | /carrinho/finalizar | Sessão + Token opcional | Cria pedido, geocodifica, calcula taxa |

### pedidos.py — Prefixo: `/pedidos`
| Método | Path | Auth | Descrição |
|--------|------|------|-----------|
| POST | /pedidos/ | Token Restaurante | Cria pedido + despacho automático |
| GET | /pedidos/ | Token Restaurante | Lista pedidos do restaurante |

### gps.py — Prefixo: `/api/gps`
| Método | Path | Auth | Descrição |
|--------|------|------|-----------|
| POST | /api/gps/update | Público | Atualiza GPS do motoboy (a cada 10s) |
| GET | /api/gps/motoboys/{restaurante_id} | Público | Lista motoboys online com GPS |
| GET | /api/gps/historico/{motoboy_id} | Público | Histórico GPS (?limite=100) |

### upload.py — Prefixo: `/api/upload`
| Método | Path | Auth | Descrição |
|--------|------|------|-----------|
| POST | /api/upload/imagem | Público | Upload + resize + WebP (tipo: logo/banner/produto/combo/categoria) |

### WebSocket (main.py)
| Path | Descrição |
|------|-----------|
| `/ws/{restaurante_id}` | Broadcast de mensagens por restaurante |

### SPA React (main.py)
| Path | Descrição |
|------|-----------|
| `/cliente/{codigo_acesso}` | Serve React SPA com código injetado |
| `/cliente/{codigo_acesso}/{path}` | Catch-all para SPA routing |

---

## 🔐 AUTENTICAÇÃO

### Restaurante (auth.py)
- **Algoritmo:** HS256 + bcrypt
- **Token:** JWT 24h via OAuth2PasswordBearer
- **SECRET_KEY:** variável `.env`
- **Dependency:** `get_current_restaurante(token, db)`

### Cliente (auth_cliente.py)
- **Algoritmo:** HS256 + bcrypt
- **Token:** JWT 72h via Header Authorization Bearer
- **SECRET_KEY:** variável `.env` ou fallback dev
- **Dependencies:** `get_cliente_atual()`, `get_cliente_opcional()`

### Motoboy / Super Admin (Streamlit)
- **Hash:** SHA256 com `.strip()`
- **Sem JWT** — autenticação via session_state

---

## ⚛️ REACT SPA (restaurante-pedido-online/)

### Rotas (App.tsx)
| Path | Componente | Descrição |
|------|-----------|-----------|
| / | Home | Cardápio com categorias, combos, produtos |
| /product/:id | ProductDetail | Detalhe do produto com variações |
| /cart | Cart | Carrinho de compras |
| /checkout | Checkout | Finalização do pedido |
| /orders | Orders | Histórico de pedidos (logado) |
| /order-success/:id | OrderSuccess | Confirmação do pedido |
| /order/:id | OrderTracking | Acompanhamento em tempo real |
| /loyalty | Loyalty | Programa de fidelidade |
| /login | Login | Login / Cadastro |
| /account | Account | Minha Conta (perfil, endereços) |

### Contexts
- **RestauranteContext:** siteInfo + CSS variables (--cor-primaria, --cor-secundaria)
- **AuthContext:** JWT token (sf_token), cache cliente (sf_cliente), sync multi-aba
- **ThemeContext:** light/dark

### Cache (useQueries.ts)
| Dado | staleTime | Descrição |
|------|-----------|-----------|
| siteInfo | 60 min | Nome, cores, horário |
| categorias | 15 min | Categorias do menu |
| produtos | 5 min | Produtos por categoria |
| combos | 15 min | Combos/ofertas |
| carrinho | 30 seg | Dado em tempo real |
| meusPedidos | 1 min | Status muda frequentemente |
| enderecos | 5 min | Muda quando cliente edita |
| pontosFidelidade | 5 min | Após pedidos/resgates |
| premiosFidelidade | 15 min | Raramente muda |

### apiClient.ts (30+ funções)
- Interceptor request: X-Session-ID + Bearer token
- Interceptor response 401: auto-logout (exceto rotas /auth)
- Funções: getSiteInfo, getCategorias, getProdutos, getCarrinho, adicionarAoCarrinho, finalizarPedido, loginCliente, registrarCliente, getEnderecos, getMeusPedidos, getCombos, getPromocoes, validarCupom, getTrackingPedido, etc.

---

## 🔗 MAPA DE DEPENDÊNCIAS

| Se mudar... | Afeta... |
|-------------|----------|
| `database/models.py` | backend/app/models.py, todos os routers, todos os Streamlit apps, migrations |
| `backend/app/schemas/*` | routers que usam esses schemas |
| `site_schemas.py` | site_cliente.py, apiClient.ts, useQueries.ts, todas as pages React |
| `carrinho_schemas.py` | carrinho.py, Checkout.tsx, Cart.tsx |
| `cliente_schemas.py` | auth_cliente.py, Login.tsx, Account.tsx |
| `apiClient.ts` | todas as pages React, useQueries.ts |
| `useQueries.ts` | todas as pages React que usam hooks |
| `RestauranteContext.tsx` | todas as pages React (via useRestaurante) |
| `AuthContext.tsx` | pages que verificam login (Orders, Account, Checkout) |
| `ConfigRestaurante` (model) | cálculo de taxa, despacho, motoboy_selector, tsp_optimizer |
| `SiteConfig` (model) | site_cliente.py, RestauranteContext, Home.tsx |
| `utils/motoboy_selector.py` | restaurante_app.py (despacho), motoboy_app.py |
| `utils/calculos.py` | restaurante_app.py, motoboy_app.py (ganhos) |

---

## 🔄 PADRÕES DO PROJETO

### CRUD padrão (FastAPI)
```python
@router.get("/{codigo_acesso}/recurso")
def listar(codigo_acesso: str, db: Session = Depends(database.get_db)):
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper(),
        models.Restaurante.ativo == True
    ).first()
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")
    itens = db.query(models.Modelo).filter(
        models.Modelo.restaurante_id == restaurante.id,
        models.Modelo.ativo == True
    ).all()
    return itens
```

### Sessão Streamlit
```python
from database.session import get_db_session
db = get_db_session()
try:
    # operações
    db.commit()
finally:
    db.close()
```

### React Query (fetching)
```tsx
// CORRETO — usar hook de useQueries.ts
const { data, isLoading } = useCategorias();

// ERRADO — nunca fazer isso
const [data, setData] = useState([]);
useEffect(() => { fetch(...).then(setData) }, []);
```

---

## ✅ FEATURES

### Implementadas
- ✅ Multi-tenant completo (isolamento por restaurante_id)
- ✅ Cadastro e gestão de restaurantes (Super Admin)
- ✅ Dashboard operacional do restaurante
- ✅ Gestão de cardápio (categorias, produtos, variações)
- ✅ Gestão de combos promocionais
- ✅ Carrinho de compras (sessão anônima + cliente logado)
- ✅ Checkout com cálculo de taxa de entrega
- ✅ Autocomplete de endereço (Mapbox)
- ✅ Cadastro e login de clientes (JWT + bcrypt)
- ✅ Gestão de endereços do cliente (CRUD)
- ✅ Histórico de pedidos do cliente
- ✅ Programa de fidelidade (pontos + prêmios)
- ✅ Promoções e cupons de desconto
- ✅ Despacho automático de entregas (3 modos)
- ✅ Seleção justa de motoboys (rotação por hierarquia)
- ✅ GPS em tempo real dos motoboys
- ✅ Mapa no painel do restaurante (Folium)
- ✅ App PWA para motoboys
- ✅ Controle de caixa (abertura/fechamento)
- ✅ Ranking de motoboys por performance
- ✅ Antifraude por localização (raio 50m)
- ✅ Upload e processamento de imagens (WebP)
- ✅ WebSocket para tempo real
- ✅ Site React SPA (Home, ProductDetail, Cart, Checkout, Orders, Loyalty, Login, Account, OrderTracking, OrderSuccess)

### Pendentes
- ⬚ Integração iFood
- ⬚ App nativo (WebView)
- ⬚ Recuperação de senha por SMS (Twilio/AWS SNS)
- ⬚ Push notifications para motoboy
- ⬚ Migração para PostgreSQL em produção
- ⬚ Armazenamento de imagens em S3/MinIO
- ⬚ Cache Redis para cardápios
- ⬚ Docker Compose para deploy

---

## 🖥️ COMANDOS

```bash
# Ativar ambiente
source venv/bin/activate

# Iniciar todos os serviços
./start_services.sh

# Iniciar serviços individualmente
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
streamlit run streamlit_app/super_admin.py --server.port=8501
streamlit run streamlit_app/restaurante_app.py --server.port=8502
streamlit run app_motoboy/motoboy_app.py --server.port=8503

# React SPA (desenvolvimento)
cd restaurante-pedido-online && npm run dev

# React SPA (build para produção)
cd restaurante-pedido-online && npm run build

# Banco de dados
python init_database.py
alembic upgrade head

# Parar tudo
pkill -f "uvicorn|streamlit"
```

### Variáveis de Ambiente (.env)
```env
DATABASE_URL=sqlite:///./super_food.db
MAPBOX_TOKEN=seu_token_aqui
SECRET_KEY=sua_chave_secreta
API_URL=http://127.0.0.1:8000
ENVIRONMENT=development
DEBUG=True
```

### Credenciais de Teste
| App | Usuário | Senha |
|-----|---------|-------|
| Super Admin | superadmin | SuperFood2025! |
| Restaurante Teste | teste@superfood.com | 123456 |
| Motoboy | código_restaurante + usuario + senha | Configurado no cadastro |

---

## 📊 SISTEMA DE MOTOBOYS

### Estados
- **OFFLINE** → cadastrado, nunca logou
- **ONLINE** → logou no app, disponível para entregas
- **EM ROTA** → possui entregas pendentes

### Seleção Justa
1. Filtra motoboys ONLINE + com capacidade disponível
2. Ordena por `ordem_hierarquia` (rotação)
3. Atribui rota otimizada (TSP)
4. Atualiza hierarquia após atribuição

### Modos de Despacho
| Modo | Descrição |
|------|-----------|
| rapido_economico | TSP por proximidade — otimiza combustível (padrão) |
| cronologico_inteligente | Agrupa pedidos por tempo (10 min), depois TSP |
| manual | Restaurante atribui manualmente |

### Fluxo de Entrega
```
Pedido pendente → Em Preparo → Pronto → Despacho → Motoboy recebe
→ Inicia entrega → Navega (Maps/Waze) → Chega → Registra pagamento
→ Entregue (ganho calculado) → Disponível para próxima
```

### Cálculo de Ganho do Motoboy
```
ganho = valor_base_motoboy + max(0, distancia_km - distancia_base_motoboy_km) × valor_km_extra_motoboy
```

---

## 📁 SEEDS (database/seed/)

| Arquivo | O que cria |
|---------|-----------|
| seed_001_super_admin.py | Super admin padrão (superadmin/SuperFood2025!) |
| seed_002_planos.py | Planos de assinatura (Básico, Essencial, Avançado, Premium) |
| seed_003_restaurante_teste.py | Restaurante demo |
| seed_004_categorias_padrao.py | Categorias de menu padrão |
| seed_005_config_padrao.py | ConfigRestaurante padrão |
| seed_006_produtos_pizzaria.py | 23 produtos de pizzaria + variações |
