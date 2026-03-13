# CLAUDE.md — Super Food

## REGRAS

1. Responder **sempre em português**.
2. Gerar **codigo completo**, nunca snippets parciais.
3. **TODAS** as queries filtram por `restaurante_id` (multi-tenant).
4. No React, usar hooks de `hooks/useQueries.ts` — **NUNCA** useState+useEffect manual para fetching.
5. Senhas **SEMPRE** com `.strip()` antes de hash.
6. Interceptor 401 ja existe no `apiClient.ts` — nao duplicar.
7. **NUNCA** armazenar objetos ORM no `session_state`.
8. Ao concluir cada etapa do plano, marcar com (x) e data.
9. Se a sessao morrer, retomar do ultimo checkpoint marcado.
10. **REGRA CRITICA:** Marcar `[x]` com data **IMEDIATAMENTE** apos concluir cada tarefa, ANTES de prosseguir para a proxima. Nunca deixar tarefas concluidas sem marcacao.
11. **PROTOCOLO DE AUDITORIA OBRIGATORIO:** Apos **CADA etapa concluida** da migracao Streamlit → React, executar:
    - **Passo 1:** Auditar o codigo React implementado (listar funcionalidades, fluxos, campos, validacoes)
    - **Passo 2:** Auditar o codigo original Streamlit correspondente (mesmas informacoes)
    - **Passo 3:** Cruzar as duas auditorias e listar TODAS as diferencas encontradas
    - **Passo 4:** Corrigir cada diferenca no React ate atingir paridade funcional com o Streamlit
    - **Passo 5:** Verificar build (`npm run check`) sem erros antes de marcar como concluido
    - _Usar agentes paralelos (Task tool) para as auditorias quando possivel para economizar tempo._
12. **GESTAO AUTOMATICA DE MEMORIA (OBRIGATORIO):**
    O Claude Code **DEVE** gerenciar sua propria memoria de forma proativa e autonoma, sem o usuario precisar pedir.
    - **Diretorio:** `/home/pcempresa/.claude/projects/-home-pcempresa-Documentos-super-food/memory/`
    - **AO INICIAR cada sessao:**
      1. Ler `MEMORY.md` (carregado automaticamente) para contexto rapido
      2. Ler os arquivos de topico relevantes para a tarefa atual (ex: `architecture.md`, `corrections-log.md`)
      3. **NAO** re-ler arquivos que ja foram lidos e estao na memoria — economizar tokens
    - **DURANTE a sessao:**
      1. Ao descobrir padroes, bugs, decisoes tecnicas → salvar imediatamente no arquivo de topico adequado
      2. Ao concluir uma tarefa/sprint → atualizar `MEMORY.md` com novo estado
      3. Ao modificar arquivos importantes → atualizar `architecture.md` se a estrutura mudar
      4. Ao encontrar e corrigir bugs → registrar em `corrections-log.md`
    - **AO FINALIZAR a sessao (ou ao perceber que o contexto esta grande):**
      1. Atualizar `MEMORY.md` com: sprint/tarefa atual, o que foi feito, proximos passos
      2. Atualizar `CLAUDE.md` secao "ESTADO ATUAL DO PROJETO" com progresso
      3. **Limpar** informacoes obsoletas dos arquivos de memoria (remover tarefas ja concluidas ha muito tempo, erros ja resolvidos, etc.)
      4. Manter `MEMORY.md` com no maximo 150 linhas (conciso e util)
    - **Arquivos de memoria padrao:**
      - `MEMORY.md` — estado atual, resumo, links para topicos (SEMPRE conciso, <150 linhas)
      - `architecture.md` — caminhos, stack, hooks, decisoes tecnicas
      - `corrections-log.md` — historico de bugs/correcoes (limpar entradas antigas periodicamente)
      - Criar novos arquivos por topico conforme necessidade (ex: `sprint3-motoboy.md`)
    - **Arquivos de referencia do projeto (somente leitura — NAO editar sem pedir):**
      - `README.md` — documentacao oficial do projeto (700+ linhas). Contém: stack, instalacao, endpoints, fluxos, arquitetura cloud, roadmap, changelog. **Consultar ANTES de tomar decisoes arquiteturais.** Atualizar somente quando: nova versao, novo sprint concluido, novo endpoint, ou mudanca de stack.
      - `ESTRUTURA.md` — arvore de pastas + fluxo de dados detalhado
    - **Principio:** O usuario **NUNCA** deve precisar dizer "lembre disso" ou "atualize a memoria". O Claude Code faz isso sozinho, automaticamente, como parte natural do trabalho.

---

## ESTADO ATUAL DO PROJETO

- **Sprint atual:** Sprint 11 — Deploy Fly.io — **EM PROGRESSO**
- **Tarefa atual:** Deploy concluido! App rodando em https://superfood-api.fly.dev
- **Status:** Sprint 10 COMPLETO (Streamlit removido, tag v4.0.0). Sprint 11: 11.1-11.4 parcialmente concluidos
- **Ultima sessao:** 13/03/2026 — Deploy Fly.io com PostgreSQL + Redis + Alembic migrations
- **Proxima etapa:** 11.4 testes finais, 11.5 dominio, 11.6 monitoramento
- **Bugs conhecidos:** Nenhum critico pendente

---

## DEPLOY — COMO SUBIR PARA PRODUÇÃO

**Comando único (na pasta raiz do projeto):**
```bash
~/.fly/bin/fly deploy
```

**O Dockerfile faz tudo automaticamente:**
1. Build React (Node 20)
2. Instala deps Python
3. Na inicialização: `alembic upgrade head` → migrations automáticas
4. Inicia Gunicorn com 2 workers Uvicorn

**Infraestrutura Fly.io (já configurada):**
- App: `superfood-api` — https://superfood-api.fly.dev
- PostgreSQL: `superfood-db` (GRU) — conectado automaticamente via DATABASE_URL
- Redis: Upstash — conectado via REDIS_URL
- Secrets: já configurados (SECRET_KEY, SUPER_ADMIN_USER/PASS, MAPBOX_TOKEN, REDIS_URL)

**Verificar depois do deploy:**
```bash
~/.fly/bin/fly logs --app superfood-api  # ver logs
curl https://superfood-api.fly.dev/health  # verificar saúde
```

**IMPORTANTE — Ambiente local vs produção:**
- Local: SQLite + `create_all` automático (ENVIRONMENT não é "production")
- Produção: PostgreSQL + Alembic migrations (ENVIRONMENT=production no fly.toml)
- Para adicionar migration nova: criar arquivo em `migrations/versions/` e rodar `fly deploy`

---

## ESTRUTURA DO PROJETO

```
super-food/
├── backend/                          # FastAPI Backend
│   └── app/
│       ├── main.py                  # Entry point FastAPI (serve SPA React)
│       ├── routers/                 # Rotas API modulares
│       │   ├── auth_restaurante.py  # Auth JWT restaurante
│       │   ├── auth_cliente.py      # Auth cliente
│       │   ├── painel.py            # Todas rotas /painel/* (admin)
│       │   ├── site_cliente.py      # Rotas site público
│       │   ├── carrinho.py          # Carrinho/checkout
│       │   ├── upload.py            # Upload imagens (JWT)
│       │   ├── pedidos.py           # Pedidos legado
│       │   ├── restaurantes.py      # Restaurantes legado
│       │   └── motoboys.py         # GPS motoboys
│       ├── models.py               # SQLAlchemy ORM models
│       ├── database.py             # Config BD SQLite/PostgreSQL
│       ├── auth.py                 # JWT helpers
│       └── utils/                  # Helpers (despacho, menus)
│
├── restaurante-pedido-online/       # FRONTEND VITE + REACT
│   ├── package.json                # Scripts: dev, build, check
│   ├── vite.config.ts              # Build config (proxy, aliases)
│   ├── tsconfig.json               # TypeScript config
│   ├── dist/public/                # BUILD OUTPUT (servido pelo FastAPI)
│   └── client/
│       ├── index.html              # HTML raiz Vite
│       └── src/
│           ├── main.tsx            # Entry point React
│           ├── App.tsx             # Router principal (cliente + admin)
│           ├── index.css           # Estilos globais + Tailwind
│           ├── pages/              # Paginas site cliente
│           ├── components/         # Componentes UI compartilhados (shadcn)
│           ├── hooks/              # Hooks cliente
│           ├── contexts/           # RestauranteContext, AuthContext, ThemeContext
│           └── admin/              # PAINEL ADMIN REACT
│               ├── AdminApp.tsx    # Router admin (protegido)
│               ├── contexts/       # AdminAuthContext.tsx
│               ├── lib/            # adminApiClient.ts (axios + JWT)
│               ├── hooks/          # useAdminQueries.ts, useWebSocket.ts
│               ├── pages/          # 20 paginas (Dashboard, Pedidos, etc.)
│               └── components/     # AdminLayout, Sidebar, Topbar
│
├── streamlit_app/                   # LEGADO (sera aposentado Sprint 8)
├── app_motoboy/                     # LEGADO (sera aposentado Sprint 8)
├── database/                        # Seed data
├── migrations/                      # Alembic migrations
├── run_production.py               # Script iniciar servicos
├── requirements.txt                # Deps Python
└── CLAUDE.md                       # Este arquivo
```

**Stack:**
- **Backend:** FastAPI + SQLAlchemy + JWT (authlib) + WebSocket
- **Frontend:** React 19 + TypeScript + Vite + Tailwind CSS 4 + TanStack Query v5
- **Router:** wouter | **UI:** shadcn/radix-ui | **Graficos:** recharts | **Mapa:** mapbox-gl
- **Carousel:** embla-carousel | **Build output:** `dist/public/` servido pelo FastAPI

---

## PLANO DE EXECUCAO — MIGRACAO v4.0 (Streamlit -> React + Cloud)

**Meta:** Sistema 100% React, zero Streamlit, pronto para deploy cloud com 1000 restaurantes.

---

### SPRINT 0: Correcoes Pre-Migracao ✅ COMPLETO

1. [x] Fix bug upload logo/banner (14/02)
2. [x] Limpar arquivos lixo da raiz (15/02)
3. [x] .env ja no .gitignore (15/02)
4. [x] Fix carrinho.py longitude_entrega (15/02)
5. [x] Auth JWT no upload.py (15/02)
6. [x] Fix restaurantes.py campos inexistentes (15/02)
7. [x] Fix pedidos.py campos inexistentes (15/02)

---

### SPRINT 1: API Endpoints — Painel Restaurante

> Criar endpoints REST para o React consumir. Streamlit continua funcionando em paralelo.

**1.1 Auth Restaurante**
8. [x] `POST /auth/restaurante/login` (15/02)
9. [x] `GET /auth/restaurante/me` (15/02)
10. [x] `PUT /auth/restaurante/perfil` (15/02)
11. [x] `PUT /auth/restaurante/senha` (15/02)

**1.2 Dashboard / Metricas**
12. [x] `GET /painel/dashboard` (15/02)
13. [x] `GET /painel/dashboard/grafico` (15/02)

**1.3 Pedidos**
14. [x] `GET /painel/pedidos` (15/02)
15. [x] `GET /painel/pedidos/{id}` (15/02)
16. [x] `POST /painel/pedidos` (15/02)
17. [x] `PUT /painel/pedidos/{id}/status` (15/02)
18. [x] `POST /painel/pedidos/{id}/despachar` (15/02)
19. [x] `PUT /painel/pedidos/{id}/cancelar` (15/02)

**1.4 Categorias**
20. [x] `GET /painel/categorias` (15/02)
21. [x] `POST /painel/categorias` (15/02)
22. [x] `PUT /painel/categorias/{id}` (15/02)
23. [x] `DELETE /painel/categorias/{id}` (15/02)
24. [x] `PUT /painel/categorias/reordenar` (15/02)

**1.5 Produtos**
25. [x] `GET /painel/produtos` (15/02)
26. [x] `GET /painel/produtos/{id}` (15/02)
27. [x] `POST /painel/produtos` (15/02)
28. [x] `PUT /painel/produtos/{id}` (15/02)
29. [x] `DELETE /painel/produtos/{id}` (15/02)
30. [x] `PUT /painel/produtos/{id}/disponibilidade` (15/02)

**1.6 Variacoes**
31. [x] `GET /painel/produtos/{id}/variacoes` (15/02)
32. [x] `POST /painel/produtos/{id}/variacoes` (15/02)
33. [x] `PUT /painel/variacoes/{id}` (15/02)
34. [x] `DELETE /painel/variacoes/{id}` (15/02)

**1.7 Combos**
35. [x] `GET /painel/combos` (15/02)
36. [x] `POST /painel/combos` (15/02)
37. [x] `PUT /painel/combos/{id}` (15/02)
38. [x] `DELETE /painel/combos/{id}` (15/02)

**1.8 Motoboys**
39. [x] `GET /painel/motoboys` (15/02)
40. [x] `POST /painel/motoboys` (15/02)
41. [x] `PUT /painel/motoboys/{id}` (15/02)
42. [x] `DELETE /painel/motoboys/{id}` (15/02)
43. [x] `PUT /painel/motoboys/{id}/hierarquia` (15/02)
44. [x] `GET /painel/motoboys/ranking` (15/02)
45. [x] `GET /painel/motoboys/solicitacoes` (15/02)
46. [x] `PUT /painel/motoboys/solicitacoes/{id}` (15/02)

**1.9 Caixa**
47. [x] `GET /painel/caixa/atual` (15/02)
48. [x] `POST /painel/caixa/abrir` (15/02)
49. [x] `POST /painel/caixa/movimentacao` (15/02)
50. [x] `POST /painel/caixa/fechar` (15/02)
51. [x] `GET /painel/caixa/historico` (15/02)

**1.10 Configuracoes**
52. [x] `GET /painel/config` (15/02)
53. [x] `PUT /painel/config` (15/02)
54. [x] `GET /painel/config/site` (15/02)
55. [x] `PUT /painel/config/site` (15/02)

**1.11 Bairros**
56. [x] `GET /painel/bairros` (15/02)
57. [x] `POST /painel/bairros` (15/02)
58. [x] `PUT /painel/bairros/{id}` (15/02)
59. [x] `DELETE /painel/bairros/{id}` (15/02)

**1.12 Promocoes**
60. [x] `GET /painel/promocoes` (15/02)
61. [x] `POST /painel/promocoes` (15/02)
62. [x] `PUT /painel/promocoes/{id}` (15/02)
63. [x] `DELETE /painel/promocoes/{id}` (15/02)

**1.13 Fidelidade**
64. [x] `GET /painel/fidelidade/premios` (15/02)
65. [x] `POST /painel/fidelidade/premios` (15/02)
66. [x] `PUT /painel/fidelidade/premios/{id}` (15/02)
67. [x] `DELETE /painel/fidelidade/premios/{id}` (15/02)

**1.14 Relatorios**
68. [x] `GET /painel/relatorios/vendas` (15/02)
69. [x] `GET /painel/relatorios/motoboys` (15/02)
70. [x] `GET /painel/relatorios/produtos` (15/02)
71. [x] `POST /painel/produtos/carregar-modelo` (15/02)

---

### SPRINT 2: React — Painel Restaurante

> Pasta: `restaurante-pedido-online/client/src/admin/`

**2.1 Estrutura Base** ✅ COMPLETO
72. [x] Estrutura de pastas admin/ (pages, components, hooks, contexts) (15/02)
73. [x] AdminAuthContext.tsx (15/02)
74. [x] adminApiClient.ts (15/02)
75. [x] useAdminQueries.ts (15/02)
76. [x] AdminApp.tsx (router + protecao de rota) (15/02)
77. [x] Layout base: sidebar + topbar + content area (15/02)

**2.2 Paginas** ✅ COMPLETO
78. [x] AdminLogin.tsx (15/02)
79. [x] Dashboard.tsx (15/02)
80. [x] Pedidos.tsx (16/02)
81. [x] PedidoDetalhe.tsx (16/02)
82. [x] NovoPedido.tsx (16/02)
83. [x] Categorias.tsx (drag & drop) (16/02)
84. [x] Produtos.tsx (16/02)
85. [x] ProdutoForm.tsx (+ variacoes inline) (16/02)
86. [x] Combos.tsx (16/02)
87. [x] Motoboys.tsx (com ranking + solicitacoes) (16/02)
88. [x] MotoboyDetalhe.tsx (integrado em Motoboys.tsx com tabs) (16/02)
89. [x] MapaMotoboys.tsx (Mapbox GL JS) (16/02)
90. [x] Caixa.tsx (16/02)
91. [x] ConfigRestaurante.tsx (unificado em Configuracoes.tsx) (16/02)
92. [x] ConfigSite.tsx (unificado em Configuracoes.tsx) (16/02)
93. [x] Bairros.tsx (16/02)
94. [x] Promocoes.tsx (16/02)
95. [x] Fidelidade.tsx (16/02)
96. [x] Relatorios.tsx (vendas, motoboys, produtos + CSV) (16/02)

**2.3 Tempo Real** ✅ COMPLETO
97. [x] useWebSocket hook (16/02)
98. [x] Notificacoes sonoras novos pedidos (16/02)
99. [x] Auto-refresh via WebSocket (16/02)

**2.4 Build**
100. [x] Vite config (admin + site cliente) (16/02)
101. [x] FastAPI serve React admin (16/02)
102. [x] npm run build sem erros (22/02)
103. [ ] Testes manuais

---

### SPRINT 3: API Endpoints — App Motoboy

104. [x] `POST /auth/motoboy/login` (08/03)
105. [x] `GET /auth/motoboy/me` (08/03)
106. [x] `GET /motoboy/entregas/pendentes` (08/03)
107. [x] `GET /motoboy/entregas/em-rota` (08/03)
108. [x] `POST /motoboy/entregas/{id}/iniciar` (08/03)
109. [x] `POST /motoboy/entregas/{id}/finalizar` (08/03)
110. [x] `GET /motoboy/entregas/historico` (08/03)
111. [x] `PUT /motoboy/status` (08/03)
112. [x] GPS auth JWT no endpoint existente (08/03)
113. [x] `GET /motoboy/estatisticas` (08/03)
114. [x] `GET /motoboy/ganhos/detalhado` (08/03)

---

### SPRINT 4: React — App Motoboy (PWA)

> Pasta: `restaurante-pedido-online/client/src/motoboy/`

115. [x] MotoboyAuthContext.tsx (08/03)
116. [x] motoboyApiClient.ts (08/03)
117. [x] MotoboyApp.tsx (08/03)
118. [x] MotoboyLogin.tsx + MotoboyCadastro.tsx (08/03)
119. [x] MotoboyHome.tsx (08/03)
120. [x] MotoboyEntrega.tsx (state machine completa: em_rota→no_destino→pagamento→finalizar) (08/03)
121. [x] MotoboyFinalizar.tsx (integrado em MotoboyEntrega.tsx) (08/03)
122. [x] MotoboyGanhos.tsx (com verificacao permitir_ver_saldo) (08/03)
123. [x] MotoboyHistorico.tsx (integrado em MotoboyGanhos.tsx com Base+Extra) (08/03)
124. [x] Service Worker + manifest.json (08/03)
125. [x] GPS background via useGPS hook (watchPosition + envio 10s) (08/03)
126. [x] Push notifications (Web Push API + useNotificacaoSonora) (08/03)
127. [x] npm run build sem erros (08/03)
128. [x] FastAPI serve em /entregador (08/03)

---

### SPRINT 5: API Endpoints — Super Admin ✅ COMPLETO

129. [x] `POST /auth/admin/login` (08/03)
130. [x] `GET /auth/admin/me` (08/03)
131. [x] `GET /admin/restaurantes` (08/03)
132. [x] `POST /admin/restaurantes` (08/03)
133. [x] `PUT /admin/restaurantes/{id}` (08/03)
134. [x] `PUT /admin/restaurantes/{id}/status` (08/03)
135. [x] `GET /admin/planos` (08/03)
136. [x] `PUT /admin/planos/{id}` (08/03)
137. [x] `GET /admin/metricas` (08/03)
138. [x] `GET /admin/inadimplentes` (08/03)

---

### SPRINT 6: React — Super Admin ✅ COMPLETO

139. [x] SuperAdminAuthContext.tsx (08/03)
140. [x] superAdminApiClient.ts (08/03)
141. [x] SuperAdminApp.tsx (08/03)
142. [x] AdminDashboard.tsx (08/03)
143. [x] GerenciarRestaurantes.tsx (08/03)
144. [x] NovoRestaurante.tsx (08/03)
145. [x] GerenciarPlanos.tsx (08/03)
146. [x] Inadimplentes.tsx (08/03)
147. [x] npm run build sem erros (08/03)
148. [x] FastAPI serve em /superadmin (08/03)

---

### SPRINT 7: Infraestrutura Cloud ✅ COMPLETO

**7.1 Banco**
149. [x] PostgreSQL + testar queries (08/03)
150. [x] Indices compostos — ja existiam 45+ indices em models.py (08/03)
151. [x] PgBouncer (08/03)
152. [x] Seed 1000 restaurantes (08/03)

**7.2 Imagens**
153. [x] S3/R2 — storage.py com LocalStorageBackend + R2StorageBackend (08/03)
154. [x] upload.py usar Storage abstraction (08/03)
155. [x] CDN Cloudflare — config pronta, Caddyfile com cache headers (08/03)
156. [x] Script migrar imagens existentes (08/03)

**7.3 Dominios**
157. [x] Model DominioPersonalizado (08/03)
158. [x] Migration Alembic — model pronto, rodar alembic revision (08/03)
159. [x] Endpoint configurar dominio — POST/GET/DELETE /painel/dominios (08/03)
160. [x] Endpoint verificar DNS — POST /painel/dominios/{id}/verificar (08/03)
161. [x] Middleware Host header -> restaurante_id — DomainTenantMiddleware (08/03)
162. [x] Caddy reverse proxy + SSL — Caddyfile + Dockerfile Caddy (08/03)
163. [x] Wildcard DNS *.superfood.com.br — config Cloudflare documentada (08/03)
164. [x] Documentacao CNAME — docs/dominios-personalizados.md (08/03)

**7.4 Docker**
165. [x] Dockerfile multi-stage (Node build + Python API) (08/03)
166. [x] docker-compose.yml (dev: postgres + redis + api) (08/03)
167. [x] docker-compose.prod.yml (prod: + pgbouncer + caddy + replicas) (08/03)
168. [x] Health checks — /health, /health/live, /health/ready (08/03)
169. [x] Script deploy + .env.example + .dockerignore (08/03)

**7.5 Performance**
170. [x] Redis cache cardapios — cache.py + cache em site_cliente.py (08/03)
171. [x] Redis WebSocket Pub/Sub — websocket_manager.py (08/03)
172. [x] Rate limiting — rate_limit.py com sliding window Redis (08/03)
173. [x] Gzip — GZipMiddleware + Caddy Brotli em prod (08/03)

**7.6 Monitoramento**
174. [x] Logging JSON — logging_config.py (dev colorido, prod JSON) (08/03)
175. [x] Health check endpoint — /health + /health/live + /health/ready (08/03)
176. [x] Metricas performance — metrics.py + GET /metrics (08/03)

---

### SPRINT 8: Grande Auditoria e Correções — Paridade Funcional

> Testar TODAS as páginas React vs Streamlit. Cada funcionalidade deve estar 100% funcional.
> Auditar tela por tela, campo por campo, fluxo por fluxo. Corrigir tudo antes de avançar.

**8.1 Painel Restaurante (/admin) — Auditoria Completa**
177. [x] Login restaurante — testar com credenciais existentes (08/03)
178. [x] Dashboard — métricas, gráficos, dados carregando corretamente (08/03)
179. [x] Configurações Restaurante — salvar localização (lat/lng), horários, taxas, raio entrega (08/03)
180. [x] Configurações Site — logo, banner, cores, tipo restaurante, WhatsApp, pagamentos (08/03)
181. [x] Categorias — CRUD completo, drag & drop reordenar, ativar/desativar (08/03)
182. [x] Produtos — CRUD completo, imagem upload, variações inline, disponibilidade (08/03)
183. [x] Cardápio visual — verificar se produtos aparecem corretamente no site cliente após cadastro (08/03)
184. [x] Combos — CRUD completo, itens do combo, imagem, datas (08/03)
185. [x] Pedidos — listar, filtrar por status, ver detalhes, criar pedido manual (08/03)
186. [x] Pedidos — alterar status (pendente→preparo→pronto→entrega→entregue), cancelar (08/03)
187. [x] Pedidos — despachar para motoboy, notificação sonora novos pedidos (08/03)
188. [x] Motoboys — CRUD, ranking, solicitações, hierarquia (08/03)
189. [x] Mapa Motoboys — Mapbox carregando, GPS em tempo real (08/03)
190. [x] Caixa — abrir, movimentações (entrada/saída), fechar, histórico (08/03)
191. [x] Bairros — CRUD, taxa por bairro, tempo estimado (08/03)
192. [x] Promoções — CRUD, cupom, tipo desconto, datas, limites uso (08/03)
193. [x] Fidelidade — prêmios CRUD, pontos (08/03)
194. [x] Relatórios — vendas (período), motoboys, produtos mais vendidos, exportar CSV (08/03)
195. [x] Upload de imagens — logo, banner, produto, combo (testar todos tipos) (08/03)
196. [x] WebSocket — novos pedidos atualizam em tempo real sem refresh (08/03)

**8.2 Site do Cliente (/cliente/{codigo}) — Auditoria Completa**
197. [x] Página inicial — info restaurante, logo, banner, status aberto/fechado (08/03)
198. [x] Cardápio — categorias, produtos por categoria, preços, imagens (08/03)
199. [x] Busca de produtos — filtro por nome (08/03)
200. [x] Produto detalhado — variações agrupadas, preço, imagem (08/03)
201. [x] Carrinho — adicionar item, variações, quantidade +/-, remover, limpar (08/03)
202. [x] Carrinho — adicionar combo (08/03)
203. [x] Checkout — nome, telefone, endereço, forma pagamento, troco, observações (08/03)
204. [x] Validação endereço — autocomplete Mapbox, zona de cobertura, taxa entrega (08/03)
205. [x] Pedido mínimo — validar valor mínimo antes de finalizar (08/03)
206. [x] Tracking pedido — acompanhar status após finalizar (08/03)
207. [x] Promoções — listar promoções ativas, validar cupom (08/03)
208. [x] Fidelidade — pontos do cliente, resgatar prêmio (08/03)
209. [x] Bairros — taxa calculada por endereço/distância (não por seletor bairro) (08/03)
210. [x] WhatsApp — botão funcional com mensagem padrão (08/03)
211. [x] Responsividade — mobile-first, FAB carrinho, menu hamburger (08/03)

**8.3 App Motoboy (/entregador) — Auditoria Completa**
212. [x] Login motoboy — com usuário e senha (08/03)
213. [x] Cadastro/solicitação motoboy — novo motoboy se cadastra (08/03)
214. [x] Home — entregas pendentes, em rota, status online/offline (08/03)
215. [x] Aceitar entrega — iniciar rota (08/03)
216. [x] Fluxo completo: em_rota → no_destino → pagamento → finalizar (08/03)
217. [x] GPS — envio de posição em background (10s) (08/03)
218. [x] Ganhos — base + extra, verificação permitir_ver_saldo (08/03)
219. [x] Histórico entregas — lista com filtros (08/03)
220. [x] Notificação sonora — nova entrega disponível (08/03)
221. [x] PWA — instalar como app, funcionar offline básico (08/03)

**8.4 Super Admin (/superadmin) — Auditoria Completa**
222. [x] Login super admin — credenciais superadmin/SuperFood2025! (08/03)
223. [x] Dashboard — métricas globais (total restaurantes, pedidos, receita, gráficos) (08/03)
224. [x] Gerenciar Restaurantes — listar, filtrar, editar, ativar/desativar (08/03)
225. [x] Novo Restaurante — formulário completo, todos campos, validações (08/03)
226. [x] Gerenciar Planos — visualizar, editar limites/preços dos 4 planos (08/03)
227. [x] Inadimplentes — filtro tolerância, listar, ações (notificar, suspender) (08/03)

**8.5 Integrações e Fluxos End-to-End**
228. [x] Fluxo completo: criar restaurante → configurar → cadastrar cardápio → cliente faz pedido → admin recebe → despacha → motoboy entrega (08/03)
229. [x] Multi-tenant: verificar que dados de um restaurante NÃO aparecem em outro (08/03)
230. [x] Comparar cada tela React com equivalente Streamlit — listar diferenças (08/03)
231. [x] npm run check sem erros (08/03)
232. [x] npm run build sem erros (08/03)

---

### SPRINT 9: Layouts Temáticos por Tipo de Restaurante

> Replicar EXATAMENTE os modelos HTML salvos em `restaurante-pedido-online/MODELOS DE RESTAURANTES/`.
> Cada tipo terá: header, hero/banner, nav categorias, cards produto, carrinho, footer, botões, responsividade.
> O modelo Esfiharia está corrompido (página Cloudflare) — usar estilo similar ao Salgados com cores laranja/marrom.

**Paleta de Cores por Tipo (extraída dos modelos):**

| Tipo | Primária | Secundária | Body BG | Header BG | Mood |
|------|----------|-----------|---------|-----------|------|
| Pizzaria | `#e4002e` vermelho | `#ffefef` rosa | `#ffefef` | Pattern img | Italiano/clássico |
| Hamburgueria | `#ffcd00` amarelo | `#161616` preto | `#161616` | `#161616` | Dark/urbano |
| Açaí/Sorvetes | `#61269c` roxo | `#2a7e3f` verde | `#fff` branco | Pattern img | Dessert/tropical |
| Bebidas | `#e50e16` vermelho | `#f6f5f5` cinza | `#f6f5f5` | `#f6f5f5` | Clean/fresh |
| Esfiharia | `#d4880f` laranja | `#5c3310` marrom | `#fff8f0` | Pattern img | Árabe/quente |
| Restaurante | `#ff990a` laranja | `#2b2723` marrom | Pattern img | `#2b2723` | Casual/quente |
| Salgados/Doces | `#ff883a` laranja | `#fff5eb` creme | `#fff5eb` | Pattern img | Artesanal/festa |
| Sushi | `#a40000` vermelho escuro | `#1d1c1c` carvão | Pattern img | Gradient dark | Oriental/minimalista |

**Fontes por Tipo:**
- Padrão (todos): Oswald (headings) + Lato (body)
- Pizzaria: Androgyne (custom heading) + Oswald
- Hamburgueria: Oswald uppercase bold
- Sushi: Kaushan Script cursive (todos headings, nav, preços, botões)

**9.1 Sistema de Temas Base** ✅ COMPLETO
233. [x] `themeConfig.ts` — objeto completo por tipo: cores, fontes, borderRadius, headerStyle, mood (08/03)
234. [x] CSS variables dinâmicas: 25+ vars no index.css + runtime via RestauranteContext (08/03)
235. [x] Hook `useRestauranteTheme()` — aplica CSS vars no `:root` + classe theme-dark/light + data-theme (08/03)
236. [x] Importar fontes Google (Oswald, Lato, Kaushan Script) via `@import` no index.css (08/03)

**9.2 Header Temático** ✅ COMPLETO
237. [x] `RestauranteHeader.tsx` — TopBar login + header sticky + logo + busca + carrinho + mobile menu (08/03)
238. [x] Header dark (Hamburgueria, Sushi, Restaurante): fundo escuro, texto branco/amarelo (08/03)
239. [x] Header light (Bebidas): fundo claro `#f6f5f5`, texto vermelho (08/03)
240. [x] Header pattern (Pizzaria, Açaí, Salgados): backgroundImage repeat-x + borda (08/03)
241. [x] Logo responsivo: tamanho padrão vs max-width dinâmico por tipo (08/03)
242. [x] Nav menu: hover com cor do tema, transições suaves (08/03)

**9.3 Hero Banner / Slideshow** ✅ COMPLETO
243. [x] `HeroBanner.tsx` — com banner imagem, gradiente fallback, overlay adaptativo + defaultBanner (08/03)
244. [x] Banners por tipo: extraídos dos `_ficheiros/` para `client/public/themes/{tipo}/banner.png` (08/03)
245. [x] Pizzaria: banner principal 525KB + secundário extraídos (08/03)
246. [x] Hamburgueria: banner foto burger 118KB + secundário extraídos (08/03)
247. [x] Açaí: banner açaí bowl 294KB, border-radius 28px (08/03)
248. [x] Bebidas: banner 437KB, border-radius 28px (08/03)
249. [x] Salgados: banner 120KB extraído (08/03)
250. [x] Sushi: banner 87KB extraído (08/03)
251. [x] Restaurante: banner 331KB + fallback seção compacta quando sem banner (08/03)
252. [x] Responsivo: banner full-width no mobile (08/03)

**9.4 Navegação de Categorias** ✅ COMPLETO
253. [x] `CategoryNav.tsx` — scroll horizontal com setas prev/next (08/03)
254. [x] Estilo pill/tab por tipo: cores e fontes adaptativas via themeConfig (08/03)
255. [x] Ícones de categoria: emoji do banco de dados (08/03)
256. [x] Setas prev/next no carousel de categorias (08/03)
257. [x] Responsivo: scroll horizontal com fade nas bordas no mobile (08/03)

**9.5 Cards de Produto** ✅ COMPLETO
258. [x] `ProductCard.tsx` — imagem + badges + nome + descrição + preço + botão comprar (08/03)
259. [x] Imagem circular (Pizzaria) vs rounded dinâmico por tipo (16/18/28px) (08/03)
260. [x] Badges/tags: Destaque + Promo com cores do themeConfig.badgeColors (08/03)
261. [x] Botão "Comprar": verde padrão com border-bottom 3px (08/03)
262. [x] Preço: cor do tema (priceColor dinâmico) + fonte especial se aplicável (08/03)
263. [x] Carousel horizontal de cards por categoria (embla-carousel) com setas navegação (08/03)
264. [x] Responsivo: grid responsivo 2/3/4 colunas (08/03)

**9.6 Seção Combos** ✅ COMPLETO
265. [x] `ComboSection.tsx` — cards horizontais: imagem + nome + descrição + preço + botão (08/03)
266. [x] Hamburgueria: cards escuros adaptados via themeConfig (08/03)
267. [x] Restaurante: combos por dia da semana — tipo_combo=do_dia + barra dias (08/03)
268. [x] Salgados: "Kit Festa" — tipo_combo=kit_festa + badge pessoas (08/03)
269. [x] Açaí: combos montáveis — suportado via ComboSection agrupado (08/03)
270. [x] Click abre ComboDetailModal com detalhes, itens, preço e quantidade (08/03)

**9.7 Carrinho Lateral (Sidebar)** ✅ COMPLETO
271. [x] `CartSidebar.tsx` — sidebar direita fixa desktop (340px) → drawer direita mobile (08/03)
272. [x] Header: "Meu Pedido" com gradiente cor do tema (08/03)
273. [x] Controle quantidade: cores #ff0d0d (decrease) e #00b400 (increase) via themeConfig (08/03)
274. [x] Botão finalizar: verde #00b400, border-bottom 3px solid #009a00, height 48px (08/03)
275. [x] Responsivo: sidebar desktop → drawer/sheet mobile com overlay (08/03)

**9.8 Footer Temático** ✅ COMPLETO
276. [x] `FooterSection.tsx` — 3 colunas: endereço+horários | contato+WhatsApp | pagamento (08/03)
277. [x] Hamburgueria: footer amarelo #ffcd00, texto escuro (auto-detect via isColorDark) (08/03)
278. [x] Açaí: footer roxo #562a98, texto branco (08/03)
279. [x] Sushi: footer dark #1d1c1c, texto branco (08/03)
280. [x] Pizzaria/Salgados: footer com pattern image repeat-x (suporte headerPattern) (08/03)
281. [x] Bebidas/Salgados: footer com borda superior colorida via footerBorderTop (08/03)

**9.9 Modais Temáticos**
282. [x] Modal montador pizza (Pizzaria): stepper existente em ProductDetail.tsx com tematização (08/03)
283. [x] Modal upsell (Açaí): "Monte seu Açaí" com adicionais +/- quantidade inline (08/03)
284. [x] Modal combo: ComboDetailModal com itens, preços, economia e quantidade (08/03)
285. [x] Modal verificação idade (Bebidas): AgeVerification.tsx + useAgeVerification hook (08/03)
286. [x] Todos modais: seguem paleta de cor do tema ativo (08/03)

**9.10 Features Únicas por Tipo**
287. [x] Pizzaria: montador de pizza — stepper em ProductDetail.tsx (max_sabores>1) (08/03)
288. [x] Hamburgueria: tema dark completo via isDark + CSS vars adaptativas (08/03)
289. [x] Açaí: upsell items inline com +/- quantidade por addon em ProductDetail (08/03)
290. [x] Bebidas: verificação de idade no primeiro acesso (AgeVerification + sessionStorage) (08/03)
291. [x] Restaurante: combos do dia (tipo_combo=do_dia + dia_semana + filtro backend) (08/03)
292. [x] Salgados: kits festa (tipo_combo=kit_festa + quantidade_pessoas) (08/03)
293. [x] Sushi: fonte cursiva Kaushan Script em TODOS textos via CSS [data-theme="sushi"] (08/03)

**9.11 Assets e Imagens** ✅ COMPLETO
294. [x] Extrair banners/imagens de cada `_ficheiros/` → `client/public/themes/{tipo}/banner.png` (08/03)
295. [x] Modelos não usam patterns CSS — gradientes definidos no themeConfig (08/03)
296. [x] Lazy loading adicionado no HeroBanner.tsx (loading="lazy") (08/03)
297. [x] Fallback: defaultBanner do themeConfig usado quando restaurante não tem banner (08/03)

**9.12 Config no Painel Admin** ✅ COMPLETO
298. [x] Seletor de tipo_restaurante no cadastro SuperAdmin — usa tiposRestaurante do themeConfig (08/03)
299. [x] Preview do tema no painel do restaurante (Configuracoes.tsx) — mini preview visual (08/03)
300. [x] Override de cores: cor primária/secundária personalizada sobrescreve preset (08/03)
301. [x] Upload de banner customizado — já existia, integrado com HeroBanner (08/03)

**9.13 Responsividade (replicar modelos)** ✅ COMPLETO
302. [x] Grid responsivo: 2 cols mobile → 3 cols tablet → 4 cols desktop (08/03)
303. [x] Layout 1 coluna mobile, grid md em cards de combo (08/03)
304. [x] Header: menu hamburger no mobile, nav categorias scroll horizontal (08/03)
305. [x] Banner: full-width responsivo (08/03)
306. [x] Footer: grid responsivo 1→3 colunas (08/03)
307. [x] Meta viewport: já configurado no index.html (08/03)

**9.14 Testes e Validação**
308. [x] Seed com 1 restaurante de cada tipo (08/03)
309. [ ] Comparar visual lado a lado com modelo HTML original (pixel-perfect)
310. [ ] Testar mobile (Chrome DevTools: iPhone SE, iPhone 14, Galaxy S21)
311. [ ] Testar desktop (1280px, 1440px, 1920px)
312. [x] npm run build sem erros (08/03)
313. [ ] Screenshot de cada layout (mobile + desktop) para documentação

---

### SPRINT 10: Aposentar Streamlit ✅ COMPLETO

314. [x] Validar 100% funcionalidades restaurante (12/03)
315. [x] Validar 100% funcionalidades motoboy (12/03)
316. [x] Validar 100% funcionalidades super admin (12/03)
317. [x] Remover streamlit_app/ (12/03)
318. [x] Remover app_motoboy/ (12/03)
319. [x] Remover streamlit do requirements.txt (12/03)
320. [x] Atualizar start_services.sh (12/03)
321. [x] Atualizar documentacao (12/03)
322. [x] Tag v4.0.0 (12/03)

---

### SPRINT 11: Deploy Fly.io (Produção)

> Última etapa: subir tudo para a nuvem. Fly.io região GRU (São Paulo).

**11.1 Setup Inicial** ✅ COMPLETO
323. [x] Instalar CLI Fly.io (12/03)
324. [x] `fly auth login` — kleniltonportugal@gmail.com (12/03)
325. [x] `fly apps create superfood-api --region gru` (12/03)

**11.2 Banco e Cache** ✅ COMPLETO
326. [x] `fly postgres create --region gru --name superfood-db` (12/03)
327. [x] `fly postgres attach superfood-db` — DATABASE_URL configurada (12/03)
328. [x] `fly redis create --region gru --name superfood-redis` — Upstash Redis (12/03)
329. [x] REDIS_URL configurada via `fly secrets set` (12/03)

**11.3 Secrets** ✅ COMPLETO
330. [x] `fly secrets set SECRET_KEY, SUPER_ADMIN_USER/PASS, MAPBOX_TOKEN, REDIS_URL, etc.` (12/03)
331. [x] Verificar todos secrets: `fly secrets list` (12/03)

**11.4 Deploy** ✅ PARCIAL
332. [x] `fly deploy` — app rodando em https://superfood-api.fly.dev (13/03)
333. [x] Alembic migrations rodando automaticamente no CMD do Dockerfile (13/03)
334. [x] Health check OK: `{"status":"healthy","checks":{"api":"ok","database":"ok","redis":"ok"}}` (13/03)
335. [x] Login super admin OK — JWT gerado com sucesso (13/03)
336. [ ] Testar criar restaurante + site cliente

**11.5 Uploads Persistentes** ✅ COMPLETO
337. [x] Volume Fly.io `superfood_uploads` (1GB, criptografado, snapshots automáticos) criado em GRU (13/03)
338. [x] Montado em `/app/backend/static/uploads` via `fly.toml` seção `[mounts]` (13/03)
339. [x] Uploads de imagens persistem entre deploys (13/03)

> **REGRA CRÍTICA DE DEPLOY:** Imagens são armazenadas no volume persistente.
> O volume NÃO é recriado entre deploys. Deploys são seguros para dados de upload.
> **NUNCA** deletar o volume `superfood_uploads` sem migrar os arquivos antes.
> Para verificar: `fly volumes list` | Para backup: `fly volumes snapshots list vol_ID`
>
> **Limite atual:** 1GB (volume Fly.io). Quando atingir ~700MB ou ~50 restaurantes
> ativos com muitas fotos, migrar para Cloudflare R2 (já implementado em `storage.py`).
> Migração: Sprint 12 abaixo.

**11.6 Domínio (quando comprar)**
340. [ ] Comprar domínio em Registro.br ou Cloudflare
341. [ ] `fly certs add superfood.com.br`
342. [ ] Configurar DNS: A record → IP do Fly.io
343. [ ] Testar HTTPS no domínio final

**11.7 Monitoramento**
344. [x] `fly logs` — logs verificados em tempo real (13/03)
345. [x] `fly status` — instância rodando GRU, 2/2 checks passing (13/03)
346. [ ] Configurar alertas de downtime (Fly.io dashboard)

---

### SPRINT 12: Migração Storage para Cloudflare R2 (quando necessário)

> **Quando executar:** Quando volume atingir ~700MB OU ~50+ restaurantes ativos com muitas fotos.
> **Por que R2:** Armazenamento ilimitado, CDN global, free tier 10GB/mês, independente da máquina.
> O código R2 já existe em `backend/app/storage.py` (R2StorageBackend), pronto para uso.

**12.1 Setup Cloudflare R2**
347. [ ] Criar conta Cloudflare (se não tiver)
348. [ ] Criar bucket R2 `superfood-uploads` no dashboard Cloudflare
349. [ ] Gerar Access Key ID + Secret (R2 API tokens)
350. [ ] Configurar domínio público do bucket (CDN): `cdn.superfood.com.br/` ou similar

**12.2 Migração de Arquivos**
351. [ ] Script migrar imagens do volume Fly.io → R2 (já existe em `backend/app/migrate_images.py`)
352. [ ] Atualizar URLs no banco: `/static/uploads/X` → `https://cdn.superfood.com.br/X`
353. [ ] Testar que todas imagens carregam via CDN

**12.3 Ativar R2 em Produção**
354. [ ] `fly secrets set R2_ENDPOINT=... R2_ACCESS_KEY_ID=... R2_SECRET_ACCESS_KEY=... R2_BUCKET_NAME=superfood-uploads CDN_URL=https://cdn.superfood.com.br`
355. [ ] Alterar `fly.toml`: `STORAGE_BACKEND = "r2"` (trocar de "local" para "r2")
356. [ ] `fly deploy` — novos uploads vão direto para R2
357. [ ] Verificar que uploads novos funcionam via R2/CDN
358. [ ] Remover seção `[mounts]` do `fly.toml` (volume não mais necessário)
359. [ ] `fly volumes delete vol_ID` — liberar volume após confirmar migração completa
