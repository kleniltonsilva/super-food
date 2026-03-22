# Derekh Food — Documentação Técnica Completa

> Documento de referência para vendas, marketing e suporte técnico.
> Versão 4.0.0 | Última atualização: Março 2026

---

## 1. VISÃO GERAL DO SISTEMA

- Derekh Food é um SaaS multi-tenant de delivery completo para restaurantes
- Público-alvo: pizzarias, lanchonetes, hamburguerias, açaiterias, padarias, restaurantes em geral
- 7 aplicações integradas num único sistema:
  1. API Backend (FastAPI)
  2. Super Admin (gestão da plataforma)
  3. Painel do Restaurante (gestão completa)
  4. App Motoboy (PWA)
  5. Site do Cliente (cardápio online)
  6. Cozinha Digital KDS (PWA)
  7. App Garçom (planejado)

### Diferenciais
- Sistema 100% brasileiro, desenvolvido em português
- Multi-tenant: 1 instância serve todos os restaurantes
- Layouts temáticos por tipo de restaurante (8 temas)
- Sem necessidade de app nativo — PWA funciona em qualquer celular
- Tempo real: WebSocket para notificações instantâneas
- Integrações marketplace: iFood, 99Food, Rappi, Keeta
- Sistema de billing integrado (Asaas)
- Pix Online para clientes (Woovi/OpenPix)

---

## 2. PAINEL DO RESTAURANTE (ADMIN) — Manual Completo

### 2.1 Dashboard
- Métricas em tempo real: pedidos hoje, faturamento, ticket médio, pedidos por hora
- Gráficos: vendas por dia (últimos 7 dias), vendas por forma de pagamento
- Alertas: restaurante aberto/fechado, caixa aberto/fechado
- Cards de status: pedidos pendentes, em preparo, prontos, em entrega
- Atualização automática via WebSocket (sem refresh manual)

### 2.2 Pedidos
- **Listagem em tempo real** com filtros por status e busca por nome/comanda
- **Aba Ativos:** pedidos em andamento com timer visual (verde < 15min, amarelo < 30min, vermelho > 30min)
- **Aba Mesas:** pedidos de mesa com grid visual de mesas
- **Aba Histórico:** pedidos entregues/cancelados com filtro por data e total de receita
- **Fluxo de status:** Pendente → Em Preparo → Pronto → Em Entrega → Entregue
  - Auto-aceitar: restaurantes podem configurar aceite automático para clientes recorrentes
- **Ações por pedido:** ver detalhes, imprimir comanda, mudar status, cancelar (com senha para finalizados)
- **Despacho:** automático (rápido/cronológico) ou manual (admin escolhe motoboy)
- **Integração KDS:** quando ativado, pedido vai automaticamente para cozinha digital
- **Origem do pedido:** badges visuais (iFood, 99Food, Rappi, Keeta, Web, Manual)
- **Borda vermelha:** pedidos ativos há mais de 30 min recebem destaque visual

### 2.3 Categorias
- CRUD completo de categorias do cardápio (Pizzas, Bebidas, Sobremesas etc.)
- Reordenação drag-and-drop para definir ordem no site do cliente
- Ativação/desativação individual
- Ícone emoji ou classe CSS personalizável
- Imagem de capa da categoria
- Setor de impressão: geral, cozinha, bar, caixa

### 2.4 Produtos
- CRUD completo com upload de imagem
- Campos: nome, descrição, preço, preço promocional, categoria, destaque
- **Variações:** tamanho, sabor, borda, adicional, ponto da carne
  - Cada variação com preço adicional, ordem de exibição, estoque
- **Pizza especial:** modo pizza habilitável com máximo de sabores por tamanho
  - Precificação: "mais caro" (cobra pelo sabor mais caro) ou "proporcional"
  - Ingredientes adicionais globais configuráveis por restaurante
- Controle de estoque: ilimitado ou quantidade definida
- Disponibilidade on/off (indisponível some do site sem deletar)
- Galeria de imagens adicionais
- Ingredientes em JSON para listagem no site

### 2.5 Combos
- Promoções agrupadas com vários produtos
- 3 tipos: Padrão, Combo do Dia (por dia da semana), Kit Festa (por número de pessoas)
- Preço combo vs preço original (mostra economia)
- Período de validade com data início/fim
- Imagem e descrição próprias
- Ativação/desativação

### 2.6 Motoboys
- Cadastro: nome, usuário, telefone, CPF, hierarquia
- Status: pendente, ativo, inativo, excluído (reativável em 30 dias)
- **Ranking de entregadores:** baseado em entregas realizadas, tempo médio, distância
- **Solicitações:** motoboys se cadastram pelo app → admin aprova/rejeita
- Configuração de hierarquia (posição na fila de rotação)
- Capacidade de entregas simultâneas configurável
- Edição de senha, ativação/desativação individual

### 2.7 Mapa de Motoboys
- Rastreamento GPS em tempo real no mapa (Mapbox GL)
- Visualização de todos os motoboys com status (online/offline, disponível/em rota)
- Posição do restaurante como referência central
- Atualização automática da posição via WebSocket
- Filtro por status do motoboy
- Raio de entrega visual no mapa

### 2.8 Cozinha Digital (KDS)
- **Configuração:** ativar/desativar KDS, tempos de alerta (amarelo) e crítico (vermelho)
- **Cozinheiros:** CRUD com nome, login, senha, avatar emoji
  - Modo "Todos os produtos" ou "Produtos específicos" (seleciona quais prepara)
- **Monitor:** contadores em tempo real — pedidos novos, fazendo, feitos, prontos
- **Fluxo:** Novo → Fazendo (COMECEI) → Feito (FEITO) → Pronto (despacho)
- **Aba Desempenho:** ranking de cozinheiros por tempo médio de montagem e despacho

### 2.9 Caixa
- **Abertura:** operador + valor inicial (fundo de caixa)
- **Movimentações:** vendas automáticas (ao entregar pedido), reforços, sangrias manuais
  - Classificação por forma de pagamento: dinheiro, cartão, Pix, vale
- **Fechamento:** valor contado vs valor calculado → mostra diferença (sobra/falta)
- **Operadores:** cadastro de operadores com senha individual
  - Gerente usa senha do restaurante (não precisa de operador)
- **Histórico:** lista de caixas anteriores com totais

### 2.10 Promoções
- Cupons de desconto com código
- Tipo: percentual ou valor fixo
- Valor mínimo do pedido para aplicar
- Desconto máximo (para percentual)
- Período de validade (data início/fim)
- Limite de usos total
- Ativação/desativação

### 2.11 Fidelidade
- Sistema de pontos por pedido (configurável por restaurante)
- **Prêmios resgatáveis:** desconto, item grátis, brinde
  - Cada prêmio com custo em pontos, descrição, valor
- Histórico de transações (ganhos e resgates)
- Saldo de pontos exibido no site do cliente

### 2.12 Bairros
- Zonas de entrega por bairro
- Taxa de entrega personalizada por bairro
- Tempo estimado de entrega por bairro
- Ativação/desativação por bairro
- Alternativa ao cálculo por distância (km)

### 2.13 Relatórios
- **Vendas:** gráfico de barras por período, total de pedidos, faturamento
- **Motoboys:** ranking por entregas realizadas, tempo médio, km percorridos
- **Produtos:** mais vendidos, receita por produto
- Filtros por período (hoje, 7 dias, 30 dias, personalizado)
- Gráficos interativos (Recharts)

### 2.14 Histórico de Atrasos
- Monitoramento automático de atrasos em pedidos
- Alerta quando entrega ultrapassa tempo estimado + tolerância configurável
- Tipos: atraso de entrega, retirada, mesa
- Resolução automática quando pedido é finalizado
- Sugestões de ajuste de tempo baseadas no histórico

### 2.15 Integrações Marketplace
- Conectar restaurante ao iFood, 99Food, Rappi, Keeta
- Receber pedidos do marketplace direto no painel
- Sincronização de status bidirecional
- Badge visual identificando origem do pedido
- Credenciais gerenciadas pelo Super Admin (1 credencial da plataforma por marketplace)
- Cada restaurante autoriza individualmente

### 2.16 Pagamento Pix Online (Woovi/OpenPix)
- **Adesão com consentimento:** formulário com chave Pix + tipo + aceite de termos
- **Custo:** R$0,85 por transação Pix (cobrado pela Woovi) — Derekh não cobra nada
- **Subconta virtual:** restaurante não precisa criar conta Woovi
- **Dashboard financeiro:** saldo em tempo real, histórico de saques
- **Saque manual:** com preview de taxa (grátis para saques >= R$500)
- **Saque automático:** configura valor mínimo para saque automático
- **Fluxo:** cliente paga Pix → webhook confirma → saldo acumula → restaurante saca

### 2.17 Assinatura/Billing (Asaas)
- **Trial:** 20 dias grátis com plano Premium completo
- **Planos:** Básico, Profissional, Premium (valores configuráveis pelo Super Admin)
- **Pagamento:** Pix ou Boleto via Asaas
- **Ciclo:** mensal ou anual (20% desconto)
- **Fluxo:** trial → ativo → inadimplente → suspenso → cancelado
  - Lembretes automáticos antes do vencimento
  - Suspensão parcial (pode ver mas não operar)
  - Preservação de dados por 90 dias após cancelamento

### 2.18 Configurações
- **Loja:** nome, endereço, telefone, coordenadas GPS
- **Site:** tipo de restaurante (8 temas), cores, logo, banner, favicon
- **Operação:** horários de abertura/fechamento por dia da semana
- **Entrega:** raio, taxa base, taxa por km, distância base, valor por km
- **Motoboy:** valor base, valor km extra, taxa diária, valor lanche
- **Despacho:** modo (rápido, cronológico, manual), máx pedidos por rota
- **Pedidos online:** ativar/desativar, motivo de pausa, prazo
- **Segurança:** senha do restaurante, operadores de caixa
- **Impressão:** automática on/off, largura 58/80mm
- **Pizza:** modo de precificação (mais caro ou proporcional)

---

## 3. SISTEMA DE DESPACHO DE MOTOBOYS

### 3.1 Modo Rápido (rapido_economico)
- Padrão do sistema
- Seleciona motoboy com **menor score** usando fórmula:
  `score = entregas_hoje x 1000 + hierarquia + distancia x 10`
- Prioriza quem fez MENOS entregas no dia (distribuição justa)
- TSP (Travelling Salesman Problem) otimiza rota quando motoboy tem múltiplos pedidos

### 3.2 Modo Cronológico (cronologico_inteligente)
- Agrupa pedidos por janela temporal antes de otimizar
- Respeita FIFO (primeiro pedido, primeira entrega)
- Depois aplica TSP dentro do grupo
- Ideal para restaurantes com alto volume

### 3.3 Modo Manual
- Admin seleciona motoboy para cada pedido
- Sem otimização automática de rota
- Flexibilidade total — admin usa conhecimento local
- Ideal para operações pequenas ou situações especiais

### 3.4 Algoritmo de Seleção Justa
**Fórmula do score (menor = melhor):**
```
score = entregas_hoje x 1000 + hierarquia + distancia_km x 10
```

**Componentes:**
- `entregas_hoje x 1000`: peso dominante — quem fez menos entregas leva primeiro
- `hierarquia`: posição na fila (1 = mais prioritário)
- `distancia_km x 10`: desempate por proximidade do restaurante

### 3.5 Filtros Rígidos (eliminatórios)
Um motoboy só é elegível se TODOS os critérios forem atendidos:
1. **Status ativo** (não pendente, inativo ou excluído)
2. **Disponível** (online, flag disponivel=True)
3. **GPS atualizado** (latitude/longitude não nulos)
4. **Dentro de 50m do restaurante** (verificação GPS)
5. **Sem entregas pendentes** (entregas_pendentes = 0)

### 3.6 EXEMPLO PRÁTICO

**Cenário: Pizzaria Bella Napoli — 5 motoboys, 3 pedidos prontos**

| # | Nome | Hierarquia | Entregas Hoje | GPS (50m) | Disponível | Em Rota |
|---|------|-----------|---------------|-----------|------------|---------|
| 1 | João | 1 | 2 | Sim | Sim | Não |
| 2 | Maria | 2 | 0 | Sim | Sim | Não |
| 3 | Pedro | 3 | 2 | Sim | Sim | Não |
| 4 | Ana | 4 | 1 | Sim | Não (offline) | Não |
| 5 | Carlos | 5 | 0 | Não (sem GPS) | Sim | Não |

**Pedidos prontos:**
- #101 — Rua A (2km) — 19:00
- #102 — Rua B (5km) — 19:05
- #103 — Rua C (1km) — 19:10

---

**MODO RÁPIDO:**

Filtro rígido elimina: Ana (offline), Carlos (sem GPS) → 3 elegíveis

Scores:
- João: 2x1000 + 1 + 0.02x10 = 2001.2
- Maria: 0x1000 + 2 + 0.03x10 = 2.3
- Pedro: 2x1000 + 3 + 0.01x10 = 2003.1

Pedido #101 → **Maria** (score 2.3)
Maria sai da fila (em_rota=True)

Pedido #102 → **João** (2001.2 < 2003.1)
João sai da fila

Pedido #103 → **Pedro** (único restante)

**Resultado:** Maria→#101, João→#102, Pedro→#103
**Princípio:** Distribuição JUSTA — quem fez menos entregas leva primeiro.

---

**MODO CRONOLÓGICO:**

Mesmos filtros. Pedidos agrupados por janela temporal:
- Janela 1 (19:00-19:10): #101, #102, #103

Mesma seleção do Rápido mas respeitando FIFO:
- #101 (mais antigo) → Maria
- #102 → João
- #103 → Pedro

**Resultado:** Mesma atribuição, ordem cronológica (FIFO).

---

**MODO MANUAL:**

Admin vê lista com status:
- Maria — Disponível (0 entregas)
- João — Disponível (2 entregas)
- Pedro — Disponível (2 entregas)
- Ana — Offline
- Carlos — Sem GPS

Admin escolhe:
- #101 → Pedro (conhece a região)
- #102 → João (moto rápida)
- #103 → Maria (perto)

**Resultado:** Flexibilidade total. Sem TSP automático.

---

## 4. SITE DO CLIENTE

### 4.1 Cardápio
- Layout temático por tipo de restaurante (8 temas: pizza, hamburger, açaí, sushi, padaria, marmita, bar, geral)
- Categorias com navegação lateral
- Cards de produto com imagem, preço, descrição
- Busca por nome de produto
- Destaque para promoções e combos
- Produtos indisponíveis ficam ocultos automaticamente

### 4.2 Checkout
- **Tipo:** entrega ou retirada na loja
- **Endereço:** cadastro com autocomplete, CEP, complemento
  - Geocodificação automática (Mapbox)
  - Cálculo de taxa de entrega por distância ou por bairro
- **Pagamento:** dinheiro (com troco), cartão, Pix, vale-refeição
  - Pix Online: gera QR Code em tempo real (se restaurante ativou)
- **Cupom:** campo para código de desconto
- **Observações:** campo livre para instruções especiais
- **Pedido mínimo:** validação antes de finalizar

### 4.3 Rastreamento
- Timeline visual com todos os status do pedido
- Mapa GPS com posição do motoboy em tempo real
- Sons de notificação ao mudar status
- Tempo estimado de entrega
- Polling automático para atualização

### 4.4 Conta do Cliente
- Registro com nome, email, telefone, senha
- Login por email+senha
- Perfil editável
- Múltiplos endereços salvos (com endereço padrão)
- Histórico de pedidos

### 4.5 Fidelidade
- Saldo de pontos visível
- Catálogo de prêmios disponíveis
- Resgate direto no site
- Histórico de transações (ganhos e resgates)

---

## 5. APP MOTOBOY (PWA)

### 5.1 Login e Cadastro
- Login com código do restaurante + usuário + senha
- Cadastro: solicita ao restaurante (admin aprova)
- PWA instalável no celular (funciona offline básico)

### 5.2 Fila de Entregas
- Lista de entregas atribuídas ao motoboy
- Status visual: pendente, em rota, entregue
- Detalhes: endereço, nome cliente, valor, forma de pagamento
- Botão "Iniciar Entrega" → GPS tracking ativo

### 5.3 Entrega Ativa
- Mapa com rota até o cliente
- Botão "Abrir no Waze/Google Maps"
- Registro de pagamento na entrega: dinheiro, cartão, misto
- Botão "Finalizar Entrega" com validação GPS (50m do endereço)
- Registro de ocorrência: cliente ausente, cancelamento

### 5.4 Ganhos
- Dashboard de ganhos do dia, semana, mês
- Histórico de entregas com valor de cada uma
- Total de km percorridos
- Estatísticas: entregas realizadas, tempo médio

### 5.5 Perfil
- Toggle online/offline
- Alteração de senha
- Atualização de dados

---

## 6. COZINHA DIGITAL (KDS PWA)

### 6.1 Login Cozinheiro
- Código do restaurante + login + senha
- Interface dark theme (ideal para cozinha)
- Logo e nome do restaurante exibidos

### 6.2 Aba Preparo
- **Fila horizontal** de pedidos com timer colorido
  - Verde: < 15 min
  - Amarelo: 15-25 min (alerta)
  - Vermelho: > 25 min (crítico, pulsa)
- **Comanda detalhada:** itens com quantidades, variações, observações
- **Botão COMECEI A FAZER:** marca como "Fazendo" e vincula ao cozinheiro
- **Botão FEITO - PRÓXIMO:** marca como "Feito" e avança para próximo
- **Navegação:** setas anterior/próximo para ver fila
- **Badge de origem:** Mesa, Retirada, Delivery com ícone

### 6.3 Aba Despacho
- Pedidos com status FEITO (prontos para embalar)
- Botão **PRONTO** → marca como pronto para retirada/entrega
- Botão **REFAZER** → volta para fila de preparo
- Seção de pedidos já marcados como PRONTO (confirmação visual)

### 6.4 Sons e Alertas
- Som de novo pedido (880Hz + 1174Hz — dois tons)
- Som de "Feito" (523Hz — nota Dó)
- Som de "Pronto" (523Hz + 659Hz + 783Hz — acorde Dó maior)
- API Web Audio (sem arquivos de som externos)
- Timer pulsante vermelho para pedidos críticos

### 6.5 Modos de Operação
- **Todos:** cozinheiro vê todos os pedidos da fila
- **Individual:** cozinheiro vê apenas pedidos com produtos que ele prepara
  - Configurável: vincular cozinheiro a produtos específicos

---

## 7. SUPER ADMIN

### 7.1 Dashboard
- Métricas globais: total de restaurantes, MRR, churn rate
- Gráficos de crescimento
- Analytics por período

### 7.2 Restaurantes
- CRUD completo de restaurantes
- Filtros: status, plano, billing
- Ações: ativar/desativar, resetar senha, alterar plano
- Detalhes: config, pedidos, faturamento

### 7.3 Planos
- CRUD de planos de assinatura
- Campos: nome, valor, limite motoboys, descrição, destaque
- Ordenação para exibição na landing page

### 7.4 Billing
- MRR (Monthly Recurring Revenue) em tempo real
- Lista de inadimplentes
- Ações: criar trial, cancelar assinatura, gerar fatura manual
- Histórico de pagamentos por restaurante

### 7.5 Integrações
- Credenciais da plataforma por marketplace (iFood, 99Food, Rappi, Keeta)
- 1 credencial por marketplace (gerenciada pelo Super Admin)
- Restaurantes autorizam individualmente

### 7.6 Demos
- Restaurantes de demonstração para showcase
- Dados fictícios realistas
- Autopilot opcional (simula pedidos)

### 7.7 Erros (Sentry)
- Monitoramento de erros em tempo real
- Integração com Sentry.io
- Dashboard de erros por período

---

## 8. API TÉCNICA

### 8.1 Arquitetura
- **Framework:** FastAPI (Python 3.11+)
- **ORM:** SQLAlchemy 2.0 (async-compatible)
- **Auth:** JWT (HS256) via authlib — 5 roles:
  1. `restaurante` — dono do restaurante
  2. `motoboy` — entregador
  3. `admin` — super admin
  4. `cliente` — cliente final
  5. `cozinheiro` — operador KDS
- **WebSocket:** 3 canais em tempo real:
  1. `/ws/{restaurante_id}` — painel admin (pedidos, alertas)
  2. `/ws/motoboy/{motoboy_id}` — app motoboy (entregas, GPS)
  3. `/ws/kds/{restaurante_id}` — KDS cozinha (pedidos cozinha)
- **Cache:** Redis (Upstash) para WebSocket multi-worker e sessões
- **BD desenvolvimento:** SQLite
- **BD produção:** PostgreSQL 16

### 8.2 Endpoints por Módulo (80+)
| Módulo | Prefixo | Endpoints | Descrição |
|--------|---------|-----------|-----------|
| Painel Admin | `/painel/*` | ~30 | CRUD pedidos, produtos, categorias, motoboys, config |
| Auth Restaurante | `/auth/restaurante/*` | 3 | Login, perfil, alterar senha |
| Auth Cliente | `/auth/cliente/*` | 4 | Registro, login, perfil, alterar senha |
| Auth Motoboy | `/auth/motoboy/*` | 3 | Login, cadastro, perfil |
| Auth Cozinheiro | `/auth/cozinheiro/*` | 2 | Login, perfil (me) |
| Auth Admin | `/auth/admin/*` | 2 | Login, perfil |
| Carrinho | `/carrinho/*` | 6 | CRUD carrinho, finalizar (criar pedido) |
| Site Cliente | `/cliente/{codigo}/*` | 8 | Cardápio, busca, rastreamento, endereços |
| Motoboy | `/motoboy/*` | 6 | Entregas, GPS, ganhos, finalizar |
| KDS | `/kds/*` | 5 | Pedidos cozinha, status, assumir, refazer |
| Super Admin | `/api/admin/*` | 12 | CRUD restaurantes, planos, billing, integrações |
| Billing | `/painel/billing/*` | 5 | Assinatura, faturas, pagamento |
| Billing Admin | `/api/admin/billing/*` | 6 | MRR, inadimplentes, ações billing |
| Webhooks | `/webhooks/*` | 2 | Asaas, Woovi |
| Integrações | `/painel/integracoes/*` | 4 | Connect/disconnect marketplace |
| Upload | `/painel/upload` | 1 | Upload de imagens |
| Cozinha Admin | `/painel/cozinha/*` | 7 | CRUD cozinheiros, config, dashboard |

### 8.3 WebSocket Channels
| Canal | Auth | Eventos |
|-------|------|---------|
| `/ws/{rest_id}` | JWT restaurante | novo_pedido, pedido_atualizado, kds_status_atualizado, tempo_medio_atualizado |
| `/ws/motoboy/{id}` | JWT motoboy | nova_entrega, entrega_atualizada, gps_update |
| `/ws/kds/{rest_id}` | JWT cozinheiro | kds:novo_pedido, kds:pedido_atualizado, kds:pedido_pausado, kds:pedido_despausado |

### 8.4 Autenticação
- JWT com expiração de 24h
- 5 roles: restaurante, motoboy, admin, cliente, cozinheiro
- Senha SHA256 com .strip() antes de hash
- Interceptor 401 no frontend (auto-logout)

---

## 9. FLUXOS DE NEGÓCIO

### 9.1 Ciclo de Vida do Pedido
```
Criação (site/manual/marketplace)
    |
    v
PENDENTE --> Admin aceita --> CONFIRMADO
    |                            |
    | (auto-aceitar)             |
    v                            v
EM_PREPARO <---------------------+
    |
    | (KDS: Cozinheiro marca FEITO --> PRONTO)
    v
PRONTO --> Despacho --> EM_ENTREGA --> ENTREGUE
    |                       |
    +-- (retirada) ---------+

Em qualquer ponto: CANCELADO (com motivo)
```

### 9.2 Ciclo de Vida da Entrega
```
Pedido PRONTO
    |
    v
Selecionar motoboy (auto ou manual)
    |
    v
ATRIBUÍDA --> Motoboy aceita --> EM_ROTA
    |
    v
GPS tracking ativo --> Notificação ao cliente
    |
    v
Chegou no destino --> Registra pagamento --> ENTREGUE
    |
    +-- Ocorrência: Cliente ausente / Cancelamento
```

### 9.3 Sistema de Billing
```
Restaurante se cadastra
    |
    v
TRIAL (20 dias) --> Plano Premium completo
    |
    v (vencimento)
LEMBRETE (5 dias antes)
    |
    v
ATIVO (pagou) ou INADIMPLENTE (não pagou)
    |                    |
    |                    v (2 dias)
    |              SUSPENSO (bloqueio parcial)
    |                    |
    |                    v (15 dias)
    |              CANCELADO (preserva dados 90 dias)
    |
    v
Renovação automática --> ATIVO
```

### 9.4 Pix Online
```
Restaurante ativa Pix no painel
    | (informa chave Pix + aceita termos)
    v
Subconta virtual criada (Woovi)
    |
    v
Cliente faz pedido com Pix
    |
    v
QR Code gerado (30min validade)
    |
    v
Cliente paga --> Webhook confirma
    |
    v
Saldo acumula na subconta
    |
    v
Restaurante saca (manual ou automático)
    |-- < R$500: taxa R$1,00
    +-- >= R$500: sem taxa
```

---

## 10. INFRAESTRUTURA

### Hospedagem
- **Backend:** Fly.io (região GRU — São Paulo)
- **Banco:** PostgreSQL 16 (Fly Postgres)
- **Cache:** Redis (Upstash)
- **Uploads:** Volume persistente 1GB (migração para Cloudflare R2 quando necessário)
- **CDN:** Fly.io edge

### Stack Técnica
| Camada | Tecnologia |
|--------|-----------|
| Backend | FastAPI + SQLAlchemy 2.0 + Uvicorn |
| Frontend | React 19 + TypeScript + Vite 7 + Tailwind CSS 4 |
| UI Components | shadcn/ui + Radix UI |
| State Management | TanStack Query v5 |
| Router | wouter |
| Charts | Recharts |
| Maps | Mapbox GL |
| Auth | JWT (authlib/HS256) |
| WebSocket | FastAPI native + Redis Pub/Sub |
| Deploy | Docker multi-stage + Fly.io |
| Monitoring | Sentry |
| Billing | Asaas (Pix + Boleto) |
| Pix Online | Woovi/OpenPix |
| Marketplaces | iFood, 99Food, Rappi, Keeta |

---

*Documento gerado automaticamente pelo sistema Derekh Food v4.0.0*
*Para suporte técnico: contato@derekhfood.com.br*
