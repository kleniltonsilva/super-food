# Derekh Food — Documentação Técnica Completa

> Documento de referência para vendas, marketing e suporte técnico.
> Versão 4.0.6 | Última atualização: 28/03/2026

---

## 1. VISÃO GERAL DO SISTEMA

- Derekh Food é um SaaS multi-tenant de delivery completo para restaurantes
- Público-alvo: pizzarias, lanchonetes, hamburguerias, açaiterias, padarias, restaurantes em geral
- 9 aplicações integradas num único sistema:
  1. API Backend (FastAPI)
  2. Super Admin (gestão da plataforma)
  3. Painel do Restaurante (gestão completa)
  4. App Motoboy (PWA)
  5. Site do Cliente (cardápio online)
  6. Cozinha Digital KDS (PWA)
  7. App Garçom (PWA)
  8. Bot WhatsApp Humanoide (IA — atendimento + pedidos via WhatsApp)
  9. Bridge Printer Agent (Windows — intercepta impressões de plataformas externas)

### Diferenciais
- Sistema multi-país (BR, PT, etc.) com geocoding automático por país do restaurante
- Multi-tenant: 1 instância serve todos os restaurantes
- Layouts temáticos por tipo de restaurante (8 temas)
- Sem necessidade de app nativo — PWA funciona em qualquer celular
- Tempo real: WebSocket para notificações instantâneas
- Integrações marketplace: iFood, 99Food, Rappi, Keeta
- Sistema de billing integrado (Asaas)
- Pix Online para clientes (Woovi/OpenPix)
- Feature Flags por plano: 4 tiers (Básico→Essencial→Avançado→Premium) com 22 features controladas
- Bridge Printer IA: intercepta cupons de iFood/Rappi e converte em pedidos Derekh automaticamente

---

## 2. PAINEL DO RESTAURANTE (ADMIN) — Manual Completo

### 2.0 Navegação — Sidebar Agrupada (Reorganizada 27/03)

A sidebar do painel admin foi reorganizada de 20 itens flat para **3 grupos colapsáveis** + Dashboard fixo no topo:

```
[Dashboard]                     ← sempre visível

━━ PEDIDOS & OPERAÇÃO ━━        (colapsável)
  Pedidos | Caixa | Relatórios | Hist. Atrasos

━━ CARDÁPIO ━━                  (colapsável)
  Categorias | Produtos | Combos | Promoções | Fidelidade

━━ CONFIGURAÇÕES ━━             (colapsável)
  Restaurante | Motoboys | Mapa Entregadores | Cozinha Digital
  Garçons | Bridge Impressora | WhatsApp Humanoide
  Bairros e Taxas | Integrações | Pagamento Pix | Assinatura
```

**Comportamento:**
- Estado colapsado salvo em `localStorage` (key: `admin_sidebar_groups`)
- Grupo auto-expande quando contém a rota ativa
- Feature lock (cadeado PRO) continua por `ROUTE_FEATURE_MAP`
- **Responsivo:** md (768-1024px) sidebar compacta (64px, apenas ícones + tooltip hover), lg+ sidebar completa (256px)
- Touch targets ≥ 44px (`py-3`)
- Mobile: overlay com backdrop, fecha ao navegar

**Arquivo:** `AdminSidebar.tsx`

### 2.1 Dashboard
- **Quick Actions:** 3 cards de ação rápida no topo — Pedidos (badge pendentes), Caixa (aberto/fechado), WhatsApp Bot (ativo/inativo)
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
- **Integração KDS inteligente:**
  - Quando KDS ativo, pedidos vão **automaticamente** para a cozinha digital ao serem criados
  - Status "Pronto" é bloqueado no painel — **só o cozinheiro marca PRONTO** via KDS
  - Quando cozinheiro marca PRONTO no KDS → status do pedido atualiza automaticamente no painel
  - Tempo de preparo real calculado automaticamente (histórico do pedido)
- **Pausar pedido na cozinha:** admin pode pausar pedidos NOVOS — KDS mostra cadeado, cozinheiro não pode avançar
- **Despausar:** admin despausa e pedido volta à posição original na fila da cozinha
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
  - **Config modo preço pizza:** card inline na página de Produtos (auto-save ao mudar)
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
- **Config Pagamento (na aba Pagamentos):** valor base, km extra, taxa diária, valor lanche, permitir ver saldo, antifraude GPS (finalizar fora do raio)

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
- **Auto-envio:** pedidos criados no checkout vão automaticamente para o KDS (sem intervenção do admin)
- **Sincronização KDS→Pedido:** quando cozinheiro marca PRONTO, o status do pedido principal atualiza automaticamente
- **Pausar/Despausar:** admin pode pausar pedido NOVO na cozinha — KDS exibe cadeado, ações bloqueadas
  - Ao despausar, pedido volta à posição original na fila (por horário de criação)
- **Aba Desempenho:** ranking de cozinheiros com métricas em tempo real
  - **Tempo médio de montagem:** tempo entre FAZENDO e FEITO (habilidade do cozinheiro)
  - **Tempo médio de despacho:** tempo entre criação e PRONTO (eficiência total da cozinha)
  - Filtros por período: hoje, 7 dias, 30 dias
  - Cards resumo: total de pedidos preparados, tempo médio geral
  - Ranking com medalhas (ouro/prata/bronze), avatar emoji, tempos formatados

### 2.9 Garçons e Atendimento (App Garçom)
- **Configuração no painel:** ativar/desativar app garçom, taxa de serviço (% ou fixa), permitir cancelamento de itens
- **Garçons:** CRUD com nome, login, senha, avatar emoji, modo de seção (todas mesas, faixa, custom)
- **Monitor de mesas ativas:** sessões abertas em tempo real, fechar sessão pelo admin
- **App Garçom (PWA):** app dedicado para garçons acessarem via `/garcom`
  - Login com código do restaurante + login + senha
  - **Grid de mesas:** todas as mesas com status visual (LIVRE=verde, ABERTA=âmbar, FECHANDO=vermelho)
  - **Timer por mesa:** tempo decorrido desde abertura
  - **Abertura de mesa:** quantidade de pessoas, alergias, tags (Aniversário, VIP, Família etc.), notas
  - **Pedidos por course:** couvert, bebida, entrada, principal, sobremesa (cores distintas por etapa)
  - **Cardápio integrado:** categorias + produtos do restaurante, busca, itens esgotados
  - **Carrinho:** qtd por item, observações, seletor de course, enviar para cozinha
  - **Conta da mesa:** subtotal, taxa de serviço, total, divisão por pessoa
  - **Transferir mesa:** transfere sessão inteira para outra mesa livre
  - **Repetir rodada:** repete último pedido da mesa
  - **Cancelar itens:** garçom pode cancelar itens que ainda não foram preparados
  - **Itens esgotados:** garçom pode marcar/desmarcar produtos como esgotados
  - **Integração KDS:** pedidos vão automaticamente para a cozinha digital
  - **WebSocket:** notificações em tempo real (pedido pronto, item esgotado, mesa fechada)
  - **Sons:** notificações sonoras via Web Audio API (pedido pronto, item esgotado)
  - **Tema:** dark (bg #0a0806), accent amber (#d97706/#fbbf24), fontes Outfit + JetBrains Mono

### 2.10 Caixa
- **Abertura:** operador + valor inicial (fundo de caixa)
- **Movimentações:** vendas automáticas (ao entregar pedido), reforços, sangrias manuais
  - Classificação por forma de pagamento: dinheiro, cartão, Pix, vale
- **Fechamento:** valor contado vs valor calculado → mostra diferença (sobra/falta)
- **Operadores:** cadastro de operadores com senha individual
  - Gerente usa senha do restaurante (não precisa de operador)
- **Histórico:** lista de caixas anteriores com totais

### 2.11 Promoções
- Cupons de desconto com código
- Tipo: percentual ou valor fixo
- Valor mínimo do pedido para aplicar
- Desconto máximo (para percentual)
- Período de validade (data início/fim)
- Limite de usos total
- Ativação/desativação
- **Cupons exclusivos por cliente:** vinculados a `cliente_id`, tipos: `global`, `exclusivo`, `repescagem`
  - Cupons de repescagem gerados automaticamente (formato `VOLTA-{NOME}-{código}`)
  - Validação de propriedade: cupom exclusivo só pode ser usado pelo cliente vinculado

### 2.12 Fidelidade
- Sistema de pontos por pedido (configurável por restaurante)
- **Prêmios resgatáveis:** desconto, item grátis, brinde
  - Cada prêmio com custo em pontos, descrição, valor
- Histórico de transações (ganhos e resgates)
- Saldo de pontos exibido no site do cliente

### 2.13 Bairros
- Zonas de entrega por bairro
- Taxa de entrega personalizada por bairro
- Tempo estimado de entrega por bairro
- Ativação/desativação por bairro
- Alternativa ao cálculo por distância (km)

### 2.14 Relatórios
- **Vendas:** gráfico de barras por período, total de pedidos, faturamento
- **Motoboys:** ranking por entregas realizadas, tempo médio, km percorridos
- **Produtos:** mais vendidos, receita por produto
- Filtros por período (hoje, 7 dias, 30 dias, personalizado)
- Gráficos interativos (Recharts)

### 2.15 Histórico de Atrasos
- Monitoramento automático de atrasos em pedidos
- Alerta quando entrega ultrapassa tempo estimado + tolerância configurável
- Tipos: atraso de entrega, retirada, mesa
- Resolução automática quando pedido é finalizado
- Sugestões de ajuste de tempo baseadas no histórico

### 2.16 Integrações Marketplace
- Conectar restaurante ao iFood, 99Food, Rappi, Keeta
- Receber pedidos do marketplace direto no painel
- Sincronização de status bidirecional
- Badge visual identificando origem do pedido
- Credenciais gerenciadas pelo Super Admin (1 credencial da plataforma por marketplace)
- Cada restaurante autoriza individualmente

### 2.17 Pagamento Pix Online (Woovi/OpenPix)
- **Adesão com consentimento:** formulário com chave Pix + tipo + aceite de termos
- **Custo:** 0,80% sobre o valor de cada transação Pix (cobrado pela Woovi) — Derekh não cobra nada
- **Subconta virtual:** restaurante não precisa criar conta Woovi
- **Dashboard financeiro:** saldo em tempo real, histórico de saques
- **Saque manual:** com preview de taxa (grátis para saques >= R$500)
- **Saque automático:** configura valor mínimo para saque automático
- **Fluxo:** cliente paga Pix → webhook confirma → saldo acumula → restaurante saca

### 2.18 Assinatura/Billing (Asaas)
- **Trial:** 15 dias grátis com plano Premium completo (WhatsApp Humanoide não incluso no trial)
- **Planos:** Básico (R$169,90), Essencial (R$279,90), Avançado (R$329,90), Premium (R$527,00) — valores configuráveis pelo Super Admin
- **Pagamento:** Pix ou Boleto via Asaas
- **Ciclo:** mensal ou anual (20% desconto)
- **Fluxo:** trial → ativo → inadimplente → suspenso → cancelado
  - Lembretes automáticos antes do vencimento
  - Suspensão parcial (pode ver mas não operar)
  - Preservação de dados por 90 dias após cancelamento

### 2.19 Garçons
- **Aba Garçons:** CRUD completo (nome, login, senha, emoji avatar)
  - Modo de seção: Todas as mesas, Faixa de mesas (início-fim), Mesas específicas
  - Status ativo/inativo
- **Aba Config:**
  - Ativar/desativar app garçom (habilita login pelo app)
  - Taxa de serviço: valor fixo ou percentual do subtotal
  - Permitir cancelamento de itens pelos garçons
- **Aba Mesas Ativas:** monitor em tempo real
  - Lista de sessões abertas com mesa, garçom, pessoas, pedidos, total
  - Timer desde abertura
  - Botão fechar sessão pelo admin
  - Status visual: ABERTA (amber), FECHANDO (vermelho)

### 2.20 Configurações (Reorganizado 27/03)
- **Tab Restaurante:**
  - **Operação:** status (aberto/fechado/pausado), horários por dia da semana
  - **Entrega:** modo prioridade, tolerância atraso, máx pedidos/rota, raio, taxas
  - **Pedidos do Site:** aceitar automaticamente para clientes recorrentes
  - **Controle de Pedidos Online:** ativar/desativar pedidos/entregas, motivo, prazo
  - **Endereço:** endereço + geocodificação automática (detecta país, cidade, estado, GPS via Mapbox)
- **Tab Site/Cardápio:** logo, banner, pedido mínimo, tempos, WhatsApp, pagamentos, SEO
- **Tab Impressora:** impressão automática on/off, largura 58/80mm, agente de impressão
- **Obs:** Config pagamento motoboy → movida para página Motoboys (aba Pagamentos)
- **Obs:** Config modo preço pizza → movida para página Produtos (card inline)

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
  - **Cupons exclusivos auto-sugeridos:** banner amarelo acima do campo com cupons pessoais do cliente (repescagem, compensação), clicáveis para aplicar automaticamente
  - Validação de propriedade: cupons com `cliente_id` só podem ser usados pelo dono
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
- **Verificação de email:** código OTP 6 dígitos enviado via Resend ao registrar
  - Countdown 10 minutos visível, reenvio após 60 segundos
  - Não-bloqueante: cliente pode usar o site sem verificar (botão "Pular")
  - Badge "Verificado" (verde) ou "Não verificado" (amarelo) na página de conta
- Login por email+senha
- **Esqueci minha senha:** código OTP 6 dígitos por email, validade 10 minutos
  - Sempre retorna sucesso (segurança — não revela se email existe)
  - Nova senha + confirmação na mesma tela
- **Alterar senha:** senha atual + nova senha (na página de conta)
- Perfil editável
- Múltiplos endereços salvos (com endereço padrão)
- Histórico de pedidos
- **Cupons exclusivos:** cupons pessoais (repescagem, compensação) visíveis na conta e auto-sugeridos no checkout

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
- **Pedidos pausados:** exibidos com ícone de cadeado, fundo cinza, no final da fila
  - Mensagem "Pausado pelo admin" — ações bloqueadas até admin despausar
  - Ao despausar, volta à posição original na fila por horário de criação

### 6.3 Aba Despacho
- Pedidos com status FEITO (prontos para embalar)
- Botão **PRONTO** → marca como pronto para retirada/entrega
  - **Sincronização automática:** ao marcar PRONTO, o status do pedido principal atualiza para "pronto" no painel admin
  - Cálculo automático do `tempo_preparo_real_min` (registrado no histórico do pedido)
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

## 7. APP GARÇOM (PWA)

### 7.1 Login Garçom
- Código do restaurante + login + senha
- Interface dark theme (bg: #0a0806, accent amber #d97706)
- JWT com role=garcom, expiração 7 dias

### 7.2 Grid de Mesas
- Grid visual com todas as mesas do restaurante
- **Status por cor:** Verde=LIVRE, Amber=OCUPADA (ABERTA), Vermelho=FECHANDO
- Timer mostrando tempo desde abertura da mesa
- Badge de quantidade de pessoas e tags (VIP, Aniversário, etc.)
- Footer com estatísticas: total de mesas, livres, ocupadas
- Click em mesa LIVRE → abrir mesa | Click em mesa OCUPADA → ver detalhe

### 7.3 Abertura de Mesa
- Seletor de pessoas (1-20) com botões +/-
- Campo de alergia (texto livre)
- Tags rápidas: Aniversário, VIP, Família, Casal, Reunião, Criança
- Campo de notas adicionais
- Cria sessão ABERTA vinculada ao garçom

### 7.4 Detalhe da Mesa
- Pedidos agrupados por **course** (etapa do serviço):
  - Couvert (#78716c), Bebida (#6366f1), Entrada (#0ea5e9), Principal (#d97706), Sobremesa (#ec4899)
- Lista de itens por pedido com quantidade, observações, preço
- **Cancelar item:** botão X ao lado do item (só itens em preparo, se configuração permitir)
- **Conta:** subtotal + taxa de serviço (% ou fixo) + total
- Divisão por pessoa (total ÷ qtd_pessoas)
- **Ações:** Repetir Rodada (repete último pedido), Novo Pedido, Pedir Conta
- Banner de alergia (vermelho) quando sessão tem alergia registrada
- Botão transferir mesa

### 7.5 Cardápio / Novo Pedido
- Categorias do restaurante com ícones
- Busca por nome de produto
- **Seletor de course:** pills coloridas (Couvert/Bebida/Entrada/Principal/Sobremesa)
- Cards de produto com imagem, preço, botão +/- para quantidade
- Badge "Esgotado" para itens marcados como indisponíveis
- Observação por item (modal com textarea)
- **Carrinho (drawer):** lista de itens selecionados, qtd, observação, total
- Botão "Enviar para Cozinha" → cria pedido + envia para KDS automaticamente

### 7.6 Transferir Mesa
- Grid com apenas mesas LIVRES (verdes)
- Click transfere a sessão inteira (pedidos + dados) para nova mesa
- Mesa antiga volta a LIVRE, nova mesa fica OCUPADA

### 7.7 Itens Esgotados
- Garçom pode marcar item como esgotado (desaparece do cardápio de todos)
- Garçom pode desmarcar quando item voltar a ter estoque
- Notificação WebSocket para todos os garçons conectados

### 7.8 WebSocket e Sons
- Canal: `/ws/garcom/{restaurante_id}?token={jwt}`
- **Eventos recebidos:**
  - `garcom:pedido_pronto` → som ascendente (C5-E5-G5), toast "Pedido pronto!"
  - `garcom:item_esgotado` → som descendente (A4-F#3), toast "Item esgotado"
  - `garcom:item_disponivel` → toast "Item disponível novamente"
  - `garcom:mesa_fechada` → toast "Mesa fechada pelo admin"
- Sons via Web Audio API (sem arquivos externos)

### 7.9 Gestão Admin (Painel)
- **Aba Garçons:** CRUD completo (nome, login, senha, emoji, modo seção TODOS/FAIXA/CUSTOM, faixa de mesas)
- **Aba Config:** ativar/desativar app garçom, taxa de serviço (% ou fixo), permitir cancelamento de itens
- **Aba Mesas Ativas:** monitor em tempo real de sessões abertas com garçom, pessoas, pedidos, total, botão fechar

---

## 8. SUPER ADMIN

### 8.1 Dashboard
- Métricas globais: total de restaurantes, MRR, churn rate
- Gráficos de crescimento
- Analytics por período

### 8.2 Restaurantes
- CRUD completo de restaurantes
- Filtros: status, plano, billing
- Ações: ativar/desativar, resetar senha, alterar plano
- Detalhes: config, pedidos, faturamento

### 8.3 Planos
- CRUD de planos de assinatura
- Campos: nome, valor, limite motoboys, descrição, destaque
- Ordenação para exibição na landing page

### 8.4 Billing
- MRR (Monthly Recurring Revenue) em tempo real
- Lista de inadimplentes
- Ações: criar trial, cancelar assinatura, gerar fatura manual
- Histórico de pagamentos por restaurante

### 8.5 Integrações
- Credenciais da plataforma por marketplace (iFood, 99Food, Rappi, Keeta)
- 1 credencial por marketplace (gerenciada pelo Super Admin)
- Restaurantes autorizam individualmente

### 8.6 Demos
- Restaurantes de demonstração para showcase
- Dados fictícios realistas
- Autopilot opcional (simula pedidos)

### 8.7 Erros (Sentry)
- Monitoramento de erros em tempo real
- Integração com Sentry.io
- Dashboard de erros por período

### 8.8 Bot IA (Tokens)
- Dashboard de uso de tokens do bot WhatsApp por período (hoje / 7 dias / 30 dias)
- Cards resumo: tokens input/output, custo USD/BRL, áudios STT (Groq), restaurantes ativos
- Gráfico de linha: uso diário input vs output (recharts)
- Tabela detalhada por restaurante: nome, plano, tokens, mensagens, custo
- Pricing xAI Grok-3-fast: $5/1M input, $25/1M output
- Rota: `/bot-tokens` | Arquivo: `BotTokenDashboard.tsx`

---

## 9. API TÉCNICA

### 9.1 Arquitetura
- **Framework:** FastAPI (Python 3.11+)
- **ORM:** SQLAlchemy 2.0 (async-compatible)
- **Auth:** JWT (HS256) via authlib — 6 roles:
  1. `restaurante` — dono do restaurante
  2. `motoboy` — entregador
  3. `admin` — super admin
  4. `cliente` — cliente final
  5. `cozinheiro` — operador KDS
  6. `garcom` — garçom (atendimento mesa)
- **WebSocket:** 4 canais em tempo real:
  1. `/ws/{restaurante_id}` — painel admin (pedidos, alertas)
  2. `/ws/motoboy/{motoboy_id}` — app motoboy (entregas, GPS)
  3. `/ws/kds/{restaurante_id}` — KDS cozinha (pedidos cozinha)
  4. `/ws/garcom/{restaurante_id}` — app garçom (pedido pronto, itens esgotados)
- **Cache:** Redis (Upstash) para WebSocket multi-worker e sessões
- **BD desenvolvimento:** SQLite
- **BD produção:** PostgreSQL 16

### 9.2 Endpoints por Módulo (145+)
| Módulo | Prefixo | Endpoints | Descrição |
|--------|---------|-----------|-----------|
| Painel Admin | `/painel/*` | ~30 | CRUD pedidos, produtos, categorias, motoboys, config |
| Auth Restaurante | `/auth/restaurante/*` | 3 | Login, perfil (com features dict), alterar senha |
| Auth Cliente | `/auth/cliente/*` | 9 | Registro, login, perfil, alterar senha, verificar-email, reenviar-verificacao, esqueci-senha, redefinir-senha, alterar-senha |
| Auth Motoboy | `/auth/motoboy/*` | 3 | Login, cadastro, perfil |
| Auth Cozinheiro | `/auth/cozinheiro/*` | 2 | Login (gate kds_cozinha), perfil (me) |
| Auth Garçom | `/garcom/auth/*` | 2 | Login (gate app_garcom), perfil (me) |
| Auth Admin | `/auth/admin/*` | 2 | Login, perfil |
| Carrinho | `/carrinho/*` | 6 | CRUD carrinho, finalizar (criar pedido) |
| Site Cliente | `/cliente/{codigo}/*` | 9 | Cardápio, busca, rastreamento, endereços, meus-cupons |
| Motoboy | `/motoboy/*` | 6 | Entregas, GPS, ganhos, finalizar |
| KDS | `/kds/*` | 5 | Pedidos cozinha, status, assumir, refazer |
| Super Admin | `/api/admin/*` | 15 | CRUD restaurantes, planos, billing, integrações, **features override**, **CNPJ lookup** |
| Billing | `/painel/billing/*` | 5 | Assinatura, faturas, pagamento, planos disponíveis (com features) |
| Billing Admin | `/api/admin/billing/*` | 6 | MRR, inadimplentes, ações billing |
| Webhooks | `/webhooks/*` | 2 | Asaas, Woovi |
| Integrações | `/painel/integracoes/*` | 4 | Connect/disconnect marketplace (gate: `integracoes_marketplace`) |
| Upload | `/painel/upload` | 1 | Upload de imagens |
| Cozinha Admin | `/painel/cozinha/*` | 7 | CRUD cozinheiros, config, dashboard (gate: `kds_cozinha`) |
| App Garçom | `/garcom/*` | 10 | Mesas, sessões, pedidos, itens esgotados, cardápio |
| Garçom Admin | `/painel/garcom/*` | 6 | CRUD garçons, config, sessões (gate: `app_garcom`) |
| Bridge Printer | `/painel/bridge/*` | 10 | Parse cupom, orders, patterns CRUD, status (gate: `bridge_printer`) |
| Combos | `/painel/combos/*` | 4 | CRUD combos (gate: `combos`) |
| Promoções | `/painel/promocoes/*` | 4 | CRUD cupons/promoções (gate: `cupons_promocoes`) |
| Fidelidade | `/painel/fidelidade/*` | 4 | CRUD prêmios fidelidade (gate: `fidelidade`) |
| Domínios | `/painel/dominios/*` | 4 | CRUD domínios personalizados (gate: `dominio_personalizado`) |
| Analytics | `/painel/relatorios/analytics` | 1 | Analytics avançado (gate: `analytics_avancado`) |
| Operadores Caixa | `/painel/caixa/operadores/*` | 3 | CRUD operadores (gate: `operadores_caixa`) |
| Público | `/api/public/*` | 2 | Planos (com features) e demos para landing page |

### 9.3 WebSocket Channels
| Canal | Auth | Eventos |
|-------|------|---------|
| `/ws/{rest_id}` | JWT restaurante | novo_pedido, pedido_atualizado, kds_status_atualizado, tempo_medio_atualizado |
| `/ws/motoboy/{id}` | JWT motoboy | nova_entrega, entrega_atualizada, gps_update |
| `/ws/kds/{rest_id}` | JWT cozinheiro | kds:novo_pedido, kds:pedido_atualizado, kds:pedido_pausado, kds:pedido_despausado, kds:pedido_pronto |
| `/ws/garcom/{rest_id}` | JWT garcom | garcom:pedido_pronto, garcom:item_esgotado, garcom:item_disponivel, garcom:mesa_fechada |

### 9.4 Autenticação
- JWT com expiração de 24h (garçom: 7 dias)
- 6 roles: restaurante, motoboy, admin, cliente, cozinheiro, garcom
- Senha SHA256 com .strip() antes de hash
- Interceptor 401 no frontend (auto-logout)

---

## 10. FLUXOS DE NEGÓCIO

### 10.1 Ciclo de Vida do Pedido
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
    | [Se KDS ativo: pedido vai AUTOMATICAMENTE para cozinha digital]
    | [Admin pode PAUSAR pedido NOVO na cozinha (cadeado no KDS)]
    |
    | (KDS: COMECEI → FEITO → PRONTO)
    | [Cozinheiro marca PRONTO → status atualiza automaticamente aqui]
    v
PRONTO --> Despacho --> EM_ENTREGA --> ENTREGUE
    |                       |
    +-- (retirada) ---------+

Em qualquer ponto: CANCELADO (com motivo)
```

### 10.2 Ciclo de Vida da Entrega
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

### 10.3 Sistema de Billing
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

### 10.4 Pix Online
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

## 11. INFRAESTRUTURA

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

### Gerenciamento de Dependências

**REGRA:** Todas as dependências são pinnadas com versão exata (`==`) para evitar breaking changes silenciosos em deploy.

| Arquivo | App | Starlette | FastAPI |
|---------|-----|-----------|---------|
| `requirements.txt` | API principal | 1.0.0 | 0.135.2 |
| `Hacking-restaurant-b2b/requirements-crm.txt` | CRM Sales | 0.38.6 | 0.115.0 |

**Procedimento para atualizar dependências:**
1. Verificar changelog da dependência (breaking changes)
2. Atualizar versão no `requirements.txt`
3. `pip install -r requirements.txt` local
4. Testar servidor local (`uvicorn backend.app.main:app`)
5. Testar rotas críticas (landing, health, login, SPAs)
6. Deploy e testar em produção

**Nota histórica:** Em 24/03/2026, Starlette 1.0.0 foi instalado automaticamente em produção (dep indireta do FastAPI sem teto `>=0.46.0`), quebrando a landing page. Causa: `TemplateResponse` mudou assinatura. Fix: pinnar Starlette explicitamente + corrigir API.

---

## 12. SITE INSTITUCIONAL (LANDING PAGE)

### 12.1 Landing Page — derekhfood.com.br
- **URL:** https://derekhfood.com.br (SSL Let's Encrypt)
- **URL alternativa:** https://www.derekhfood.com.br
- **URL backend:** https://superfood-api.fly.dev
- Página de vendas com design moderno (Tailwind CSS)
- Seções: hero, funcionalidades, tipos de restaurante, planos, depoimentos, FAQ, CTA
- **CTA final (27/03):** "Comece agora com teste grátis. Sem cartão de crédito, sem burocracia. Nós montamos seu cardápio, comece a receber pedidos em minutos. Se já trabalha com plataformas como iFood, os pedidos são sincronizados com nosso sistema."
- Botão WhatsApp flutuante (SVG) para contato comercial
- **Card compacto "WhatsApp Humanoide"** na seção de planos (27/03/2026):
  - Card horizontal (ícone + texto + preço + CTA) com link âncora para seção Bia abaixo
  - Badge "Exclusivo" com ponto pulsante, preço R$99,45/mês (grátis no Premium)
  - Botão "Ver tudo que ela faz ↓" → scroll para seção Bia
- **Seção standalone "Descubra o que a Bia pode fazer"** (27/03/2026):
  - Posição: entre Números/Social Proof e FAQ
  - Background dark (#0f172a) com 3 orbs flutuantes (emerald/indigo/teal) blur 100px
  - Grid overlay sutil (linhas brancas 2% opacity, 60px)
  - **Hero:** Avatar robot com anel conic-gradient rotativo (8s) + badge "Inteligência Artificial" pulsante
  - **22 ações:** Grid filtrável (5 botões: Todas/Pedidos/Atendimento/Inteligência/Proativo), cards com hover glow emerald
  - **6 diferenciais técnicos:** Áudio bidirecional, GPS Mapbox, direto na cozinha, humanização, contexto cliente, proativa
  - **Timeline 5 workers:** Dots luminosos coloridos com scroll-reveal escalonado (0s→0.6s)
  - **8 regras configuráveis:** Toggles visuais decorativos (verde=on, cinza=off)
  - **Handoff:** Card gradient com 4 steps visuais (Cliente pede → Sirene → Você assume → Devolve pra Bia)
  - **CTAs:** "Veja a Bia em ação" (abre demo modal) + "Quero ativar" (link WhatsApp)
  - **JS:** `biaFilter(cat)` toggle cards por `data-cat`, reusa IntersectionObserver existente
  - **CSS:** ~200 linhas prefixo `bia-`, animações pure CSS (biaOrbFloat, biaRingSpin, biaPulse)
  - **Mobile-first:** 2→3→4 cols, handoff steps empilham em mobile
- **Card "Bridge Printer IA"** (funcionalidades) — redesenhado (26/03/2026):
  - Título acessível: "Todos os pedidos em um só lugar"
  - Texto focado no benefício para o restaurante, sem termos técnicos
  - Botão "Saiba mais" expansível com: problema, solução, IA que aprende, box "Em homologação" (iFood, Diddi Food)
- **Planos dinâmicos:** features carregadas via `GET /api/public/planos` (com fallback hardcoded)
- Cada plano exibe features cumulativas do tier, com destaque (bold) para features novas
- FAQ com 8 perguntas incluindo explicação do WhatsApp Humanoide
- Responsivo para mobile, tablet e desktop
- SEO otimizado (meta tags, Open Graph)
- **Quiz Diagnóstico:** formulário interativo que calcula quanto o restaurante perde sem sistema (por tipo)
- **Correção ortográfica (26/03/2026):** 23+ correções de acentuação (mês, grátis, período, dúvidas, é, já, número, opção, Relatórios, Promoções, Garçom, Integrações, Domínio, Avançado, Básico)

### 12.3 Demo WhatsApp Humanoide (Modal Interativo)
- **Botões de ativação:** 2 locais — banner WhatsApp Humanoide (planos) e FAQ
- **Modal smartphone:** em desktop simula frame de celular (380×720px, border-radius 40px); em mobile ocupa tela inteira (full-screen imersivo)
- **3 telas navegáveis:**
  1. **Seleção de restaurante** — grid 2×4 com 8 tipos (Pizzaria, Esfiharia, Hamburgueria, Sushi, Restaurante, Açaí, Bebidas, Salgados) + logo Derekh
  2. **Seleção de cenário** — lista de 20 situações cotidianas com emoji, título e descrição
  3. **Chat WhatsApp** — conversa animada com typing indicators, sons Web Audio API, horário real
- **20 cenários do dia a dia:** Pedido por Áudio, Cliente Novo, Alterar Pedido, Atraso Proativo, Avaliação 5 Estrelas, Reclamação, Item Esgotado, Repescagem CRM, Fora do Horário, Restrição Alimentar, Cancelamento, Trocar Endereço, Pedido pra Festa, Recomendação, Pedido Errado, "É Robô?", Handoff Humano, Fora da Área, Dúvida Ingredientes, Rastreio
- **160 conversas únicas:** cada cenário é adaptado ao tipo de restaurante (cardápio, preços, produtos específicos)
- **Brain Replay:** ao final da conversa, botão "🧠 Veja como o humanoide pensa" repete o chat mostrando blocos roxos com o raciocínio da IA antes de cada resposta
- **End state:** botões "Assistir novamente" (replay sem brain), "Outro cenário" (volta à lista)
- **Sons:** Web Audio API (800→1200Hz para mensagem recebida, 600→900Hz para enviada)
- **UI WhatsApp:** cores dark mode autênticas (#0b141a, #1f2c34, #005c4b, #2a3942), pattern SVG de fundo

### 12.2 Páginas Legais (Compliance)

Páginas standalone servidas por Jinja2 (mesmo padrão visual da landing — Tailwind CDN, Inter, dark theme):

| Rota | Template | Conteúdo |
|------|----------|----------|
| `GET /privacidade` | `backend/templates/privacidade.html` | Política de Privacidade (LGPD) — 11 seções, 2 públicos (B2B + consumidor final) |
| `GET /termos` | `backend/templates/termos.html` | Termos de Uso — 16 seções, contrato SaaS com tabela de planos e add-ons. Seção 7 (Pagamentos Online Pix) com 6 subseções detalhadas: 7.1 Natureza do Serviço, 7.2 Fluxo do Dinheiro, 7.3 Taxas e Custos, 7.4 Responsabilidades, 7.5 Consentimento, 7.6 Alterações nas Taxas |
| `GET /cancelamento` | `backend/templates/cancelamento.html` | Política de Cancelamento — 7 seções, direito de arrependimento (Art. 49 CDC) |
| `GET /pix-online` | `backend/templates/pix_online.html` | Página Pix Online — hero institucional, seção "Como Funciona" (4 passos visuais), taxas transparentes (0,80% Woovi, saques), calculadora interativa de taxas (somente Pix, sem Boleto), comparativo com maquininhas/concorrentes, FAQ e CTA para ativação no painel |

- **Links:** footer da landing page (coluna "Legal" + bottom bar inline)
- **Empresa:** D ALVES FREITAS DOS SANTOS DESENVOLVIMENTO DE SOFTWARE LTDA — CNPJ 65.642.226/0001-31
- **DPO:** contato@derekhfood.com.br
- **Requerido por:** Transfeera (split Pix) para aprovação de conta

### 12.4 Domínio e SSL
- Domínio: `derekhfood.com.br`
- DNS: A e AAAA apontando para Fly.io
- SSL: certificados Let's Encrypt (RSA + ECDSA) para domínio raiz e www
- Renovação automática pelo Fly.io

### 12.5 WhatsApp Comercial
- Número: +1 555-900-4563 (Facebook Business)
- Integrado à landing page (botão flutuante)
- Integrado ao site dos restaurantes (botão flutuante SVG — oculto em demos)
- Será usado pelo Sales Autopilot (bot de vendas B2B)

---

## 13. FUNCIONALIDADES POR PLANO (Feature Flags)

### 13.1 Sistema de Feature Flags

O sistema usa **comparação por tier inteiro** (1-4) com hierarquia cumulativa. Cada plano inclui tudo dos anteriores.

**Arquivos-chave:**
- `backend/app/feature_flags.py` — Registry central (PlanTier, FEATURE_TIERS, funções)
- `backend/app/feature_guard.py` — FastAPI Depends factory (`verificar_feature("key")`)
- Migration 034 — `plano_tier`, `features_override`, `features_json`

**Fluxo:**
1. Restaurante se cadastra → `plano_tier = 1` (Básico)
2. Inicia trial → `plano_tier = 4` (Premium, acesso total)
3. Seleciona plano → `plano_tier` atualizado automaticamente
4. Acessa endpoint protegido → `verificar_feature()` compara tier
5. Feature bloqueada → 403 `{"type": "feature_blocked", ...}`
6. Super Admin pode dar override via `features_override` (JSON)

### 13.2 Tabela Features por Plano

| Funcionalidade | Key | Básico (T1) | Essencial (T2) | Avançado (T3) | Premium (T4) |
|---------------|-----|:-----------:|:--------------:|:-------------:|:------------:|
| Site e Cardápio | `site_cardapio` | ✅ | ✅ | ✅ | ✅ |
| Pedidos | `pedidos` | ✅ | ✅ | ✅ | ✅ |
| Dashboard | `dashboard` | ✅ | ✅ | ✅ | ✅ |
| Caixa | `caixa` | ✅ | ✅ | ✅ | ✅ |
| Bairros e Taxas | `bairros_taxas` | ✅ | ✅ | ✅ | ✅ |
| Motoboys | `motoboys` | ✅ (2) | ✅ (5) | ✅ (10) | ✅ (ilimitados) |
| Configurações | `configuracoes` | ✅ | ✅ | ✅ | ✅ |
| Relatórios Básicos | `relatorios_basicos` | ✅ | ✅ | ✅ | ✅ |
| Cupons e Promoções | `cupons_promocoes` | — | ✅ | ✅ | ✅ |
| Programa de Fidelidade | `fidelidade` | — | ✅ | ✅ | ✅ |
| Combos Promocionais | `combos` | — | ✅ | ✅ | ✅ |
| Relatórios Avançados | `relatorios_avancados` | — | ✅ | ✅ | ✅ |
| Operadores de Caixa | `operadores_caixa` | — | ✅ | ✅ | ✅ |
| KDS Cozinha Digital | `kds_cozinha` | — | ✅ | ✅ | ✅ |
| App Garçom | `app_garcom` | — | — | ✅ | ✅ |
| Integrações Marketplace | `integracoes_marketplace` | — | — | ✅ | ✅ |
| Pix Online | `pix_online` | — | — | ✅ | ✅ |
| Domínio Personalizado | `dominio_personalizado` | — | — | ✅ | ✅ |
| Analytics Avançado | `analytics_avancado` | — | — | ✅ | ✅ |
| Bridge Printer IA | `bridge_printer` | ✅ | ✅ | ✅ | ✅ |
| Bot WhatsApp IA | `bot_whatsapp` | — | — | — | ✅ |
| Suporte Dedicado | `suporte_dedicado` | — | — | — | ✅ |

### 13.3 Endpoints Protegidos

| Feature | Endpoints | Guard |
|---------|-----------|-------|
| `combos` | GET/POST/PUT/DELETE `/painel/combos` | `verificar_feature("combos")` |
| `operadores_caixa` | GET/POST/DELETE `/painel/caixa/operadores` | `verificar_feature("operadores_caixa")` |
| `cupons_promocoes` | GET/POST/PUT/DELETE `/painel/promocoes` | `verificar_feature("cupons_promocoes")` |
| `fidelidade` | GET/POST/PUT/DELETE `/painel/fidelidade/premios` | `verificar_feature("fidelidade")` |
| `dominio_personalizado` | GET/POST/DELETE `/painel/dominios` | `verificar_feature("dominio_personalizado")` |
| `analytics_avancado` | GET `/painel/relatorios/analytics` | `verificar_feature("analytics_avancado")` |
| `kds_cozinha` | Todos `/painel/cozinha/*` + login cozinheiro | `verificar_feature("kds_cozinha")` |
| `app_garcom` | Todos `/painel/garcom/*` + login garçom | `verificar_feature("app_garcom")` |
| `bridge_printer` | Todos `/painel/bridge/*` | `verificar_feature("bridge_printer")` |
| `integracoes_marketplace` | Todos `/painel/integracoes/*` | `verificar_feature("integracoes_marketplace")` |

### 13.4 Super Admin Override

- `GET /api/admin/restaurantes/{id}/features` — lista features + overrides
- `PUT /api/admin/restaurantes/{id}/features` — body `{"kds_cozinha": true}` → dá acesso
- Override com `null` remove o override (volta ao plano)
- Armazenado em `restaurantes.features_override` (JSON)

---

## 14. Bridge Printer Agent — Sprint 21

### Arquitetura

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  Impressora Térmica  │────▶│  Bridge Agent (Win)   │────▶│  Backend Derekh │
│  (iFood/Rappi/etc)   │     │  spooler_monitor.py   │     │  /painel/bridge │
└─────────────────────┘     │  text_extractor.py    │     │  parse + orders │
                            │  bridge_client.py     │     └────────┬────────┘
                            └──────────────────────┘              │
                                                           ┌──────▼──────┐
                                                           │  Pedido no  │
                                                           │  Painel Admin│
                                                           └─────────────┘
```

### Fluxo de Interceptação

1. **Spooler Monitor** detecta novo job de impressão no Windows (polling 2s)
2. Ignora jobs com prefixo "Derekh_" (impressões do próprio sistema)
3. **Text Extractor** remove comandos ESC/POS e decodifica texto (CP860/UTF-8)
4. **Bridge Client** envia texto para `POST /painel/bridge/parse`
5. Backend tenta **padrões aprendidos** (regex por confiança decrescente)
6. Se nenhum casou → **Groq IA (Llama 3.3 70B)** extrai JSON estruturado
7. Registro salvo em `bridge_intercepted_orders` com status `pendente`
8. Operador revisa no painel e clica "Criar Pedido" (ou automático se configurado)
9. Backend cria `Pedido` com `origem=bridge_{plataforma}`, vincula cliente por telefone

### Motor de IA — Groq (NÃO Grok)

```
Prioridade:
1. GROQ_API_KEY → Groq Llama 3.3 70B (principal) + Llama 3.1 8B (fallback rate limit)
2. XAI_API_KEY  → xAI Grok Mini Fast (fallback legado)
3. Nenhuma      → Só regex patterns salvos
```

- **Groq** (groq.com) — LPU inference ultra-rápido, free tier 30 req/min
- **API:** `https://api.groq.com/openai/v1/chat/completions` (compatível OpenAI)
- **response_format:** `{"type": "json_object"}` — garante JSON válido
- **Campos extraídos:** cliente_nome, cliente_telefone, endereco, itens[], valor_total, forma_pagamento

### Ciclo de Aprendizado

```
1. Cupom novo → nenhum pattern → Groq parseia (confiança 0.3)
2. Admin clica "Validar e Aprender" no painel
3. Sistema analisa texto original + dados parseados → gera regex automáticos
4. Salva BridgePattern (confiança 0.7 — validado por humano)
5. Próximos cupons iguais → regex pega direto (sem chamar Groq)
6. Confiança sobe +0.1 a cada validação (até 1.0)
```

- Padrões são armazenados em `bridge_patterns` com regex de detecção + mapeamento de campos
- Cada uso incrementa o contador e a confiança cresce
- Padrões com confiança alta são usados antes da IA (economia de API)
- Operador pode remover padrões ruins ou re-parsear registros que falharam

### 14 Plataformas Detectadas

ifood, rappi, 99food, aiqfome, ubereats, keeta, zdelivery, anota_ai, goomer, neemo, deliverymuch, menudigital, cardapio_digital, james

### Tabelas de Banco

| Tabela | Campos principais | Descrição |
|--------|-------------------|-----------|
| `bridge_patterns` | plataforma, regex_detectar, mapeamento_json, confianca, usos | Padrões de parsing aprendidos |
| `bridge_intercepted_orders` | texto_bruto, dados_parseados, plataforma_detectada, status, pedido_id | Pedidos interceptados |

### Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/painel/bridge/parse` | Recebe texto bruto, tenta pattern/IA, salva registro |
| POST | `/painel/bridge/orders` | Cria pedido Derekh a partir de intercepted_order |
| POST | `/painel/bridge/orders/{id}/validar` | Valida parse IA + auto-gera regex pattern |
| POST | `/painel/bridge/orders/{id}/reparse` | Re-parseia com IA (para registros que falharam) |
| GET | `/painel/bridge/patterns` | Lista padrões aprendidos |
| POST | `/painel/bridge/patterns` | Criar padrão manualmente |
| PUT | `/painel/bridge/patterns/{id}` | Editar confiança/validação |
| DELETE | `/painel/bridge/patterns/{id}` | Remove padrão |
| GET | `/painel/bridge/orders` | Lista pedidos interceptados (filtro por status) |
| GET | `/painel/bridge/status` | Dashboard: estatísticas + motor IA disponível |

### Smart Client Lookup

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/painel/clientes/buscar?q=TELEFONE` | Busca cliente por telefone (min 3 chars) |

O endpoint retorna `{encontrado, cliente: {id, nome, telefone, total_pedidos, ultimo_endereco}}`.
No **NovoPedido.tsx**, ao digitar telefone, debounce 500ms busca cliente existente e exibe card verde com opção de vincular.

### Política de Cancelamentos

Pedidos criados pelo Bridge são pedidos normais do sistema. Cancelamentos devem ser feitos manualmente pelo painel (página Pedidos), não há cancelamento automático.

### Configuração no Windows

1. Instalar `DerekhFood-Bridge.exe`
2. Na janela de configuração: login com email/senha do restaurante
3. Selecionar impressoras a monitorar (checkbox)
4. Opcionalmente ativar "Criar pedido automaticamente"
5. Config salva em `%APPDATA%/DerekhBridge/bridge_config.json`

### Estrutura do Bridge Agent

```
bridge_agent/
├── main.py              — Orquestrador + system tray
├── spooler_monitor.py   — Win32 spooler polling
├── text_extractor.py    — ESC/POS → texto limpo
├── bridge_client.py     — REST client → backend
├── config.py            — Config JSON persistente
├── ui/config_window.py  — Tkinter login + settings
├── requirements.txt     — requests, pywin32, pystray, Pillow
└── build.bat            — PyInstaller → .exe
```

---

## 15. OVERHAUL CRIAÇÃO DE RESTAURANTE (Super Admin)

### 15.1 Endpoint CNPJ — BrasilAPI

- **`GET /api/admin/cnpj/{cnpj}`** — consulta dados do CNPJ via BrasilAPI
- Auth: requer super admin JWT
- Valida checksum do CNPJ antes de consultar
- Retorna: razão social, nome fantasia, endereço (logradouro, número, complemento, bairro, município, UF, CEP), telefones, email, situação cadastral
- Erros: 400 (CNPJ inválido), 404 (não encontrado), 429 (rate limit), 502/504 (BrasilAPI)

### 15.2 Validação de Telefone com DDD

- 67 DDDs brasileiros válidos no backend e frontend
- Celular (11 dígitos): deve começar com 9 após DDD
- Fixo (10 dígitos): deve começar com 2-5 após DDD
- Máscaras automáticas no frontend: `(XX) XXXXX-XXXX` / `(XX) XXXX-XXXX`

### 15.3 Validação CPF/CNPJ Frontend

- Checksum módulo 11 em tempo real (borda verde/vermelha)
- Máscara automática: `XXX.XXX.XXX-XX` (CPF) / `XX.XXX.XXX/XXXX-XX` (CNPJ)
- CNPJ válido habilita botão "Consultar Receita Federal" → auto-preenche formulário

### 15.4 Email de Boas-Vindas (Resend)

- **Serviço:** `backend/app/email_service.py` — Resend SDK
- **Template:** `backend/app/email_templates.py` — HTML responsivo
- Enviado automaticamente ao criar restaurante (checkbox "Enviar email" no form)
- Conteúdo: credenciais (código de acesso + senha), botões CTA (Painel + Guia de Início), checklist
- Graceful degradation: se `RESEND_API_KEY` não configurada, log warning, não quebra
- Secrets Fly.io: `RESEND_API_KEY`, `DEREKH_FROM_EMAIL`

### 15.5 Trial Configurável

- Default alterado de 20 para **15 dias** (`ConfigBilling.trial_dias`)
- Label dinâmico no formulário via `useBillingConfig()`
- Resposta do endpoint retorna `trial_dias` e `email_enviado`

### 15.6 Tela de Sucesso Melhorada

- Credenciais com botão copiar (clipboard)
- Badge "Email enviado para {email}" (verde) ou "Email não enviado" (amarelo)
- Badge "Trial de {N} dias iniciado" (azul)
- Botão "Abrir Guia de Início" (link para `/admin/inicio`)

### 15.7 Página de Onboarding (`/admin/inicio`)

- **Arquivo:** `src/admin/pages/Onboarding.tsx`
- **Rota:** `/admin/inicio` (protegida por PrivateRoute)
- 6 seções em Accordion:
  1. **Primeiros Passos** — configurar restaurante, cardápio, bairros
  2. **Instalar Apps (PWA)** — Motoboy, KDS, Garçom com URLs e passo-a-passo
  3. **Impressora de Cupons** — requisitos, download, configuração
  4. **Bridge Agent** — interceptar pedidos iFood/Rappi
  5. **Integrações** — iFood, Pix Online, WhatsApp Humanoide
  6. **Manual de Uso Básico** — pedidos, despacho, cardápio, relatórios

### 15.8 Arquivos do Módulo

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| `backend/app/email_service.py` | Novo | Serviço Resend (enviar_email_boas_vindas, enviar_email_generico) |
| `backend/app/email_templates.py` | Novo | Template HTML email boas-vindas |
| `backend/app/routers/admin.py` | Modificado | Endpoint CNPJ, validação DDD, envio email, campo enviar_email |
| `database/models.py` | Modificado | ConfigBilling.trial_dias default 20→15 |
| `requirements.txt` | Modificado | Adicionado resend>=2.0.0 |
| `src/superadmin/lib/validators.ts` | Novo | Máscaras + validações CPF/CNPJ/telefone/CEP/DDD |
| `src/superadmin/lib/superAdminApiClient.ts` | Modificado | consultarCnpj(), CnpjData, enviar_email |
| `src/superadmin/hooks/useSuperAdminQueries.ts` | Modificado | useConsultarCnpj() |
| `src/superadmin/pages/NovoRestaurante.tsx` | Reescrito | Formulário com máscaras, CNPJ lookup, email, tela sucesso |
| `src/admin/pages/Onboarding.tsx` | Novo | Página onboarding 6 seções |
| `src/admin/AdminApp.tsx` | Modificado | Rota /inicio |

---

## 16. Sales Autopilot — WA Sales Bot v2.0

### 16.1 Visão Geral

Bot de vendas WhatsApp para prospecção B2B de restaurantes, integrado ao CRM Sales Autopilot (`derekh-crm.fly.dev`). Estratégia dual-number: outbound (prospecção) e inbound (Fale Conosco).

### 16.2 Arquitetura

- **Arquivo principal:** `Hacking-restaurant-b2b/crm/wa_sales_bot.py`
- **Webhook:** `Hacking-restaurant-b2b/crm/app.py`
- **LLM:** Grok 3 Fast (xAI) — temperature 0.8 (conversa) / 0.85 (inbound)
- **Envio:** Evolution API (prioritário) → WhatsApp Cloud API Meta (fallback)
- **TTS:** Grok 3 Fast TTS (voz "ara") — áudio personalizado com dados iFood

### 16.3 Prompts Humanizados

O bot se apresenta como "Klenilton, vendedor humano da Derekh Food". Características:
- Tom oral com gírias brasileiras ("show", "massa", "kkk"), abreviações ("vc", "tbm", "qdo")
- Frases curtas (2-3 por mensagem), sem emojis corporativos, sem bullet points
- Táticas de venda integradas: espelhamento, dor específica, escassez real, prova social, micro-compromissos
- Dois prompts separados: `_build_system_prompt_conversa()` (conversas em andamento) e `_build_system_prompt_inbound()` (primeiro contato)

### 16.4 Intent Scoring Contextual

Substitui keywords binárias por scoring cumulativo (`INTENT_PATTERNS`):

| Categoria | Score | Descrição |
|-----------|-------|-----------|
| `high_intent` | +30 | "quanto custa", "quero contratar", "teste grátis" |
| `medium_intent` | +15 | "como funciona", "me interessa", "quero saber mais" |
| `competitor_pain` | +20 | "ifood", "comissão", "27%", "delivery tá caro" |
| `objection` | oportunidade | "caro", "vou pensar" — IA contorna, não encerra |
| `opt_out` | encerra definitivo | "sair", "stop" — remove da lista para sempre |
| `hard_no` | encerra com classe | "sem interesse", "já disse que não" — pode reativar se voltar |

Classificação: score >= 50 = interesse_alto, >= 30 = interesse, objeções = objecao, ? = duvida.

### 16.5 Handoff Gradual

3 níveis de escalação para atendimento humano:

1. **Immediate:** lead pediu demo/reunião/humano → handoff imediato + notificação ao dono
2. **Warm:** score acumulado >= 60 + 3 msgs, ou CRM score >= 85 → bot faz transição natural ("deixa eu te passar pro time técnico")
3. **Strategic:** 2+ objeções não resolvidas → "vou pedir pro meu gerente te dar um toque"

Todos os handoffs disparam `_notificar_handoff()` — envia WA ao dono com nome do restaurante, cidade, motivo e número do lead.

### 16.6 Delay Humano

`_calcular_delay_humano()`: 3-15 segundos proporcional ao tamanho da mensagem do lead (n_palavras * 0.8). Evita respostas instantâneas que denunciam automação.

### 16.7 Contexto do Lead

`_build_lead_context()` monta resumo injetado no system prompt: nome do restaurante, ratings Google/iFood, categorias, cenário (sem delivery / nota alta / popular), mensagens trocadas, objeções anteriores.

### 16.8 Anti-Loop Cross-Instance

`_BOT_PHONE_NUMBERS` em `app.py`: set com números dos próprios bots (outbound + inbound). No webhook, se remetente é um dos números do bot, ignora a mensagem — evita loop infinito quando bot A envia para número monitorado por bot B.

### 16.9 Fluxo de Processamento

```
Mensagem chega (webhook Evolution)
    |
    v
Anti-loop: é número do bot? → ignora
    |
    v
Buscar conversa (ativa → encerrada/handoff → nova)
    |
    v
Detectar intenção (scoring contextual)
    |-- opt_out → remove definitivo, despedida
    |-- hard_no → encerra com classe
    |-- outro → delay humano → IA responde
                    |
                    v
               Avaliar handoff
                    |-- immediate → notifica dono
                    |-- warm → transição natural + notifica
                    |-- strategic → escala para gerente
```

---

## 17. Bot WhatsApp Humanoide — Sprint 16

### 17.1 Visão Geral

Atendente IA humanizado que conversa com clientes no WhatsApp como se fosse uma pessoa real. Sem menus robotizados, sem "aperte 1 ou 2". O cliente manda mensagem e é atendido naturalmente: faz pedido, tira dúvidas, recebe acompanhamento. Funciona 24h/7d.

**Precificação:** Incluso grátis no plano Premium (R$527/mês). Demais planos: add-on R$99,45/mês.

### 17.2 Arquitetura

O bot roda **integrado ao backend principal** (`superfood-api.fly.dev`), não como microserviço separado.

```
backend/app/bot/
├── atendente.py          — Lógica principal (webhook → LLM → resposta)
├── context_builder.py    — Prompt em 3 camadas (sistema + restaurante + cliente)
├── function_calls.py     — 22 funções que o LLM pode chamar
├── evolution_client.py   — Client Evolution API (texto/áudio/presença/digitando)
├── xai_llm.py            — Client xAI Grok (chat completion + function calling)
├── xai_tts.py            — Client xAI TTS (gerar áudio com voz)
├── groq_stt.py           — Client Groq Whisper STT (transcrever áudio)
└── workers.py            — Workers periódicos (avaliação, repescagem, reset tokens)
```

### 17.3 Fluxo de Processamento

```
Mensagem WhatsApp → Evolution API webhook
    |
    v
POST /webhooks/evolution (resposta 200 imediata)
    |
    v
Background: processar_webhook()
    |-- Dedup por msg_id
    |-- Anti-spam lock por número (30s)
    |
    v
Identificar restaurante (por evolution_instance)
    |
    v
Se áudio: baixar via Evolution → transcrever via Groq Whisper STT
    |
    v
Buscar/criar conversa (sessão 2h)
    |
    v
Montar contexto 3 camadas:
    L1: Sistema (identidade, regras, capacidades)
    L2: Restaurante (cardápio, horário, promoções, combos)
    L3: Cliente (nome, endereço, pedidos, carrinho)
    |
    v
Presença online + "digitando..." via Evolution API
    |
    v
Loop LLM (até 5 iterações):
    xAI Grok-3-fast → function calling → executar → resultado → Grok responde
    |
    v
Decidir texto ou áudio TTS (reciprocidade: cliente mandou áudio → bot responde áudio)
    |
    v
Se texto: enviar com delay_ms=1500 (mostra "digitando..." 1.5s)
Se áudio: enviar "gravando..." 3s + PTT com delay_ms=3000
    |
    v
Salvar mensagem no BD + notificar painel via WebSocket
```

### 17.4 Tabelas de Banco (Migration 035)

| Tabela | Campos principais | Descrição |
|--------|-------------------|-----------|
| `bot_config` | restaurante_id, bot_ativo, nome_atendente, tom_personalidade, voz_tts, evolution_instance, evolution_api_url, evolution_api_key, whatsapp_numero, pode_criar/alterar/cancelar_pedido, pode_dar_desconto, pode_reembolsar, stt_ativo, tts_autonomo, max_tokens_dia | Configuração do bot por restaurante |
| `bot_conversas` | restaurante_id, telefone, cliente_id, nome_cliente, status, intencao_atual, msgs_enviadas, msgs_recebidas, usou_audio, pedido_ativo_id, itens_carrinho (JSON) | Sessões de conversa |
| `bot_mensagens` | conversa_id, direcao (recebida/enviada), tipo (texto/audio), conteudo, tokens_input, tokens_output, modelo_usado, function_calls (JSON), tempo_resposta_ms | Histórico de mensagens |
| `bot_avaliacoes` | restaurante_id, conversa_id, pedido_id, cliente_id, nota (1-5), comentario | Avaliações pós-entrega |
| `bot_problemas` | restaurante_id, conversa_id, pedido_id, tipo, descricao, resolvido | Reclamações detectadas |
| `bot_repescagem` | restaurante_id, cliente_id, tipo, mensagem, cupom_codigo, desconto_pct, enviado_em, respondido, cupom_validade_dias, lembrete_enviado, lembrete_enviado_em, canal, email_enviado, promocao_id | Campanhas de reativação |

### 17.5 Function Calls (22 funções)

| Função | Descrição |
|--------|-----------|
| `buscar_cliente` | Busca cliente pelo telefone |
| `cadastrar_cliente` | Cadastra novo cliente (nome, telefone, endereço) |
| `buscar_cardapio` | Busca itens por nome/categoria |
| `buscar_categorias` | Lista categorias disponíveis |
| `criar_pedido` | Cria pedido CONFIRMADO (vai direto para cozinha) |
| `alterar_pedido` | Adiciona/remove itens de pedido ativo |
| `cancelar_pedido` | Cancela pedido (respeita status máximo) |
| `repetir_ultimo_pedido` | Repete último pedido do cliente |
| `consultar_status_pedido` | Status do pedido ativo |
| `rastrear_pedido` | Rastreamento completo: fila cozinha, motoboy GPS, ETA |
| `verificar_horario` | Status aberto/fechado + horário |
| `buscar_promocoes` | Promoções ativas + cupons exclusivos do cliente |
| `registrar_avaliacao` | Registra nota 1-5 + comentário |
| `registrar_problema` | Registra reclamação com tipo |
| `aplicar_cupom` | Aplica cupom de desconto (valida propriedade) |
| `escalar_humano` | Notifica admin para handoff (status aguardando_handoff) |
| `trocar_item_pedido` | Troca item específico do pedido |
| `buscar_endereco` | Endereço salvo do cliente |
| `calcular_entrega` | Busca taxa de entrega por bairro |
| `gerar_pix` | Gera cobrança Pix (futuro — Módulo 1) |
| `verificar_pagamento` | Verifica status pagamento Pix (futuro) |
| `consultar_pedido` | Consulta pedido por ID ou telefone |

Pedidos criados pelo bot são automaticamente marcados com `origem = "whatsapp_bot"` e vão direto para a cozinha (quando KDS ativo).

### 17.6 LLM — xAI Grok

- **Modelo:** `grok-3-fast` (rápido, bom em português)
- **API:** `POST https://api.x.ai/v1/chat/completions`
- **Temperature:** 0.6 (precisão com naturalidade)
- **Max tokens:** 400 (mensagens curtas como WhatsApp real)
- **Function calling:** `tool_choice: "auto"`
- **Loop:** Até 5 iterações (para chains de function calls)
- **Fallback:** Se LLM falhar, responde "me dá um segundo..."

### 17.7 STT — Groq Whisper

- **Serviço:** `groq_stt.py`
- **Modelo:** Whisper Large V3 via Groq API (inference ultra-rápido)
- **API:** `POST https://api.groq.com/openai/v1/audio/transcriptions`
- **Idioma:** Auto-detectado (pt por padrão)
- **Formato:** Áudio base64 baixado via Evolution API → transcrito → texto processado

### 17.8 TTS — xAI

- **Serviço:** `xai_tts.py`
- **Endpoint:** `POST https://api.x.ai/v1/tts` (NÃO `/v1/audio/speech`)
- **Body:** `{text, voice_id, language, output_format: "wav"}`
- **Vozes disponíveis:** ara, eve, leo, rex, sal, una
- **Envio:** Via Evolution API como PTT nativo (bolinha verde) usando `sendWhatsAppAudio`
- **Critérios para enviar áudio:** cliente mandou áudio (reciprocidade) OU conversa longa (>=8 msgs)

### 17.8.1 TTS Dual-Mode (Fish Audio + xAI Grok)

#### Visão Geral

- Sistema TTS dual-mode: Fish Audio S2-Pro (quando configurado) com fallback automático para xAI Grok
- Zero breaking changes: default = Grok (comportamento idêntico ao anterior)
- Toggle via config `tts_provider`: "grok" (padrão) ou "fish"

#### Arquivos

| Arquivo | Descrição |
|---------|-----------|
| `Hacking-restaurant-b2b/crm/fish_tts.py` | Módulo Fish Audio para Sales Bot (sync, retorna path .mp3) |
| `backend/app/bot/fish_tts.py` | Módulo Fish Audio para Bot Restaurante (async, retorna base64 MP3) |
| `crm/wa_sales_bot.py` | `gerar_audio_tts()` agora verifica tts_provider antes de gerar |
| `backend/app/bot/atendente.py` | Dual-mode: Fish → fallback Grok |
| `database/models.py` | Campo `tts_provider` em BotConfig (String, default 'grok') |

#### API Fish Audio

- **Endpoint:** `POST https://api.fish.audio/v1/tts`
- **Auth:** Bearer token (header `Authorization`)
- **Model:** `s2-pro` (header, NÃO body)
- **Body:** `{text, reference_id, format, latency}`
- **Response:** binary audio stream (chunked)
- **Tags emoção S2-Pro:** livres em colchetes `[amigável]`, `[empolgado]`, etc.
- **SDK:** `pip install fish-audio-sdk` (opcional, funciona via httpx raw)

#### Variáveis de Ambiente

| Variável | Descrição | Obrigatória |
|----------|-----------|-------------|
| `FISH_API_KEY` | API key Fish Audio | Sim (para ativar) |
| `FISH_VOICE_ID` | Voice/reference_id clonada ou stock | Não |

#### Como Ativar

1. Obter API key em fish.audio (plano Plus $11/mês mínimo)
2. Definir `FISH_API_KEY` no ambiente
3. Sales Bot: `POST /api/configuracao` → `tts_provider = "fish"`
4. Bot Restaurante: setar `tts_provider = "fish"` no BotConfig do restaurante
5. Opcional: `pip install fish-audio-sdk` para usar SDK em vez de API raw

#### Tags de Emoção Fish Audio S2-Pro (Sales Bot — atualizado 27/03)

| Contexto | Tag | Uso |
|----------|-----|-----|
| abertura | `[amigável]` | Primeiro contato |
| apresentacao | `[profissional]` | Pitch de produto |
| beneficio | `[empolgado]` | Destacar vantagens |
| objecao | `[compreensivo]` | Objeções do lead |
| urgencia | `[empolgado]` | Criar senso de urgência |
| fechamento | `[empolgado]` | Fechar venda |
| followup | `[amigável]` | Follow-up |
| suporte | `[calmo]` | Suporte técnico |
| serio | `[sério]` | Contexto formal/sério |
| profissional | `[profissional]` | Pitch B2B |
| amigavel | `[amigável]` | Conversa casual |
| empolgado | `[empolgado]` | Notícia boa |
| alivio | `[aliviado]` | Resolver problema |
| pausa | `[pausa curta]` | Pausa dramática |
| risinhos | `[risinhos]` | Tom divertido |

Tags são livres (linguagem natural em colchetes) — Fish Audio S2-Pro interpreta qualquer tag.

#### Fluxo de Fallback

1. Verifica `tts_provider` config
2. Se `"fish"`: tenta Fish Audio → se falha → Grok
3. Se `"grok"` ou vazio: Grok direto (comportamento atual)
4. Se Grok falha: retorna `None` → fallback para texto

### 17.9 Context Builder — 3 Camadas

**Layer 1 — Sistema (cacheable, ~2000 tokens):**
- Identidade do atendente (nome, tom)
- Regras absolutas (nunca inventar preço, nunca revelar ser IA)
- Capacidades habilitadas (criar pedido, dar desconto, etc.)
- Comportamento quando fechado, item esgotado
- Fluxo de pedido, upsell natural
- **Regras de naturalidade (27/03/2026 — 12 correções baseadas em conversa real):**
  - Emojis: 1-2 por mensagem, NUNCA repetir mesmo emoji em mensagens consecutivas
  - Nome do cliente: máximo 2-3 vezes na conversa TODA (não a cada mensagem)
  - Cardápio: se completo → enviar POR CATEGORIA, uma de cada vez
  - Preços de tamanhos: SEMPRE preço FINAL (nunca "base + acréscimo")
  - Pizza metade/metade: cobrar pelo SABOR MAIS CARO
  - Confirmação final: SEMPRE incluir taxa entrega com bairro/distância
  - Variação de frases: alternar "Tudo certo?", "Pode ser?", "Beleza?", etc.
  - Encerramento: NÃO repetir "estou à disposição" em toda mensagem
  - Alteração de pedido: dizer APENAS o que mudou + novo total (não repetir tudo)
  - Endereço: se não encontrou → pedir endereço completo com bairro e cidade
  - Mensagens curtas: max 3 linhas por mensagem, paragrafar com linha em branco
  - Saudação: responder UMA vez (não duplicar ao receber "oi" + "quero pizza")

**Layer 2 — Restaurante (semi-fixo, ~2000 tokens):**
- Nome, endereço, horário (aberto/fechado com hora atual)
- Cardápio completo (categorias, produtos, variações, preços, promoções)
- Combos e promoções ativas
- Formas de pagamento, tempo de entrega, pedido mínimo
- Usa savepoints para queries de promoções/combos (tabelas podem não existir)

**Layer 3 — Cliente (dinâmico, ~500-1000 tokens):**
- Nome, telefone, CPF, endereço salvo
- Últimos 3 pedidos (comanda, itens, valor, status)
- Pedido ativo (se houver)
- Carrinho em construção (JSON na conversa)

### 17.10 Endpoints

**Webhook (público):**

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/webhooks/evolution` | Webhook Evolution API — resposta 200 imediata, processamento em background |

**Painel Restaurante (requer JWT + feature flag `bot_whatsapp`):**

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/painel/bot/config` | Configuração do bot |
| PUT | `/painel/bot/config` | Atualizar configuração (permissões, comportamento, voz) |
| POST | `/painel/bot/ativar` | Ativar bot (requer config prévia pelo Super Admin) |
| POST | `/painel/bot/desativar` | Desativar bot |
| GET | `/painel/bot/conversas` | Listar conversas com paginação (filtro por status, busca por nome/telefone, offset, limit) |
| GET | `/painel/bot/conversas/{id}/mensagens` | Mensagens de uma conversa com paginação (pagina, limite) |
| POST | `/painel/bot/conversas/{id}/enviar-mensagem` | Enviar mensagem manual do admin ao cliente (requer handoff) |
| POST | `/painel/bot/conversas/{id}/escalar` | Assumir controle da conversa (requer senha admin) |
| POST | `/painel/bot/conversas/{id}/recusar-handoff` | Recusar handoff — bot sugere ligar para restaurante |
| POST | `/painel/bot/conversas/{id}/devolver-bot` | Devolver conversa ao bot |
| GET | `/painel/bot/dashboard` | Dashboard — estatísticas (conversas, pedidos, faturamento, avaliação) |

**Super Admin (requer JWT admin):**

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/admin/bot/instancias` | Listar todos os bots configurados |
| POST | `/api/admin/bot/criar-instancia/{restaurante_id}` | Criar/atualizar instância bot |
| PUT | `/api/admin/bot/instancia/{config_id}` | Atualizar instância (Evolution, número, etc.) |
| DELETE | `/api/admin/bot/instancia/{config_id}` | Deletar instância |
| GET | `/api/admin/bot/token-usage` | Dashboard uso de tokens (periodo: daily/weekly/monthly, restaurante_id opcional) |

### 17.11 Workers Periódicos

- **Reset tokens diário:** Zera `tokens_usados_hoje` à meia-noite
- **Avaliação pós-entrega:** Após `delay_avaliacao_min` minutos de entrega, envia mensagem pedindo nota + broadcast `bot_mensagem` ao painel
- **Detecção de atraso:** Monitora pedidos atrasados, notifica cliente via WA e painel via `bot_atraso_detectado`
- **Repescagem avançada:** Clientes inativos há N dias recebem mensagem com cupom exclusivo (formato `VOLTA-{NOME}-{código}`)
  - Cupom personalizado por cliente, nunca repete
  - Vinculado a Promoção com `tipo_cupom='repescagem'` e `cliente_id`
  - Validade configurável (padrão 7 dias)
  - Envio via WA, email ou ambos + broadcast `bot_mensagem` ao painel
- **Lembrete de cupom:** A cada ~1h, verifica cupons exclusivos/repescagem que expiram nas próximas 24h → envia lembrete via WA + email + broadcast ao painel
- **Notificações proativas de status:** Atualiza clientes sobre mudanças de status do pedido + broadcast ao painel
- Todos os 5 workers fazem broadcast `bot_mensagem` via WebSocket ao painel admin
- Executados via `asyncio.create_task` no lifespan do FastAPI

### 17.12 Frontend Admin — BotWhatsApp.tsx

Página "Bot WhatsApp" no painel do restaurante com 5 abas:
- **Dashboard:** conversas hoje/semana, pedidos via bot, faturamento, avaliação média (tokens movidos para Super Admin)
- **Configurações:** toggle on/off, nome do atendente, permissões, comportamento
- **Conversas:** lista com paginação + **busca por nome/telefone** (debounce 500ms), badges de status (ATIVA/ADMIN/QUER HUMANO), detalhe chat view com:
  - **Handoff com senha:** quando cliente pede humano, bot notifica painel com som sirene. Admin pode aceitar (com senha) ou recusar. Se aceitar, bot para de responder. Se recusar, bot sugere ligar para restaurante.
  - **Mensagem manual:** quando em handoff, admin pode enviar mensagens diretamente ao cliente (com tag [ADMIN])
  - **Devolver ao bot:** admin pode devolver controle para o bot a qualquer momento
- **Relatórios:** estatísticas detalhadas
- **Repescagem:** lista de clientes inativos com checkboxes, envio em massa (desconto%, validade, canal WA/email/ambos), cards resumo (total inativos, enviadas, taxa retorno), histórico paginado
- Feature flag: `bot_whatsapp` (Premium ou add-on)

#### Fluxo de Handoff (Escalação para Humano)

1. Cliente pede para falar com humano → bot chama `escalar_humano` → status = `aguardando_handoff`
2. WebSocket broadcast `bot_handoff_solicitado` → **som sirene distinto** (6 bips alternados 880↔660Hz) no painel
3. Toast vermelho com botão "Atender" + notificação persistente no sino
4. Admin pode:
   - **Aceitar** (requer senha do restaurante) → status = `handoff` → bot para, admin digita mensagens
   - **Recusar** → status = `ativa` → bot envia ao cliente: "O responsável não está disponível. Ligue para {telefone}"
5. Quando admin termina → clica "Devolver ao Bot" → status = `ativa` → bot volta a responder

### 17.13 Frontend Super Admin — Modal Bot + Dashboard Tokens

Na página "Gerenciar Restaurantes" do Super Admin:
- Modal para criar/editar instância bot por restaurante
- Campos: Evolution instance, API URL, API key, número WhatsApp, nome atendente
- Toggle ativar/desativar
- Lista de todas as instâncias bot configuradas

**Página "Bot IA (Tokens)"** — rota `/bot-tokens` (`BotTokenDashboard.tsx`):
- Seletor período: Hoje / 7 dias / 30 dias
- 5 cards resumo: Total Tokens (in/out), Custo USD, Custo BRL, Áudios STT, Restaurantes ativos
- LineChart (recharts): uso diário input vs output
- Tabela: uso por restaurante ordenada por custo (nome, plano, tokens in/out, msgs, USD, BRL)
- Pricing: xAI Grok-3-fast ($5/1M input, $25/1M output)

### 17.14 Secrets Fly.io

| Secret | Descrição |
|--------|-----------|
| `XAI_API_KEY` | API key xAI para Grok LLM + TTS |
| `GROQ_API_KEY` | API key Groq para Whisper STT |

### 17.15 Bugs Corrigidos no Deploy

1. **`relation "promocoes" does not exist`** — Tabelas promoções/combos podem não existir em prod. Fix: `db.begin_nested()` savepoints no context_builder
2. **`tool_call` → `tool_choice`** — Parâmetro errado no xai_llm.py
3. **ForeignKeyViolation bot_mensagens** — `db.rollback()` em catch desfazia criação da conversa. Fix: savepoints isolam falha
4. **Evolution send 500** — Wrapped em try/except para salvar mensagem no BD mesmo se envio falhar

### 17.16 Auditoria Pós-Deploy (26/03)

**Segurança:**
- Whitelist campos admin PUT bot — `ADMIN_BOT_CAMPOS_PERMITIDOS` (antes aceitava qualquer campo via setattr)
- Whitelist restaurante: adicionados `tts_provider`, `avaliacao_lembrete_24h`, `desconto_por_review`, `desconto_review_pct`
- Warning `EVOLUTION_WEBHOOK_SECRET` não configurado em dev

**Bug do Cadeado:**
- `SelecionarPlano.tsx`: adicionado `refreshRestaurante()` no onSuccess para atualizar features no contexto
- `useFeatureFlag.ts`: corrigido `bridge_printer: 4` → `bridge_printer: 1` (espelhando backend)
- `useAdminQueries.ts`: invalidação de `planosDisponiveis` ao selecionar plano

**WebSocket/Notificações:**
- 5 workers agora broadcast `bot_mensagem` via WebSocket (antes só 1)
- Novo evento `bot_atraso_detectado` tratado no frontend (som alarme + toast + notificação)
- Novo evento `bot_handoff_solicitado` com som sirene distinto (6 bips 880↔660Hz)

**Cache Anti-spam:**
- `_limpar_cache_locks()` em atendente.py — limpa `_processing_locks` quando >100 entradas

### 17.17 Presença e Indicadores de Digitação (27/03)

Bot agora aparece "online" e mostra indicadores visuais no WhatsApp:

**Funções adicionadas em `evolution_client.py`:**
| Função | Endpoint Evolution | Descrição |
|--------|-------------------|-----------|
| `definir_presenca(instance, ...)` | `POST /instance/setPresence/{instance}` | Define presença da instância (available/unavailable) |
| `enviar_presenca_conversa(numero, ...)` | `POST /chat/sendPresence/{instance}` | Envia "digitando..." ou "gravando áudio" para conversa específica |

**Parâmetro `delay_ms` adicionado:**
- `enviar_texto()`: aceita `delay_ms` — mostra "digitando..." automaticamente antes de enviar
- `enviar_audio_ptt()`: aceita `delay_ms` — mostra "gravando áudio" antes de enviar

**Integração no `atendente.py`:**
1. Antes de chamar LLM: `definir_presenca("available")` + `enviar_presenca_conversa("composing", 15000ms)`
2. Antes de enviar texto: `enviar_texto(delay_ms=1500)` — mostra "digitando..." por 1.5s
3. Antes de enviar áudio: `enviar_presenca_conversa("recording", 3000ms)` + `enviar_audio_ptt(delay_ms=3000)`

**Resultado UX:** Bot aparece online, mostra "digitando..." enquanto pensa, mostra "gravando..." antes de áudio — comportamento idêntico a um humano.

### 17.18 Engenharia de Fala Natural — Dicção Áudio TTS (27/03)

Sistema dual que transforma texto formal do LLM em fala natural brasileira para TTS. O LLM escreve em português correto; o áudio passa por transformação antes do TTS.

**Princípio 70/30:** 70% formal + 30% informal = natural sem parecer inculto.

**Bia (Bot Restaurante — `atendente.py`):**

| Etapa | Transformação | Exemplo |
|-------|--------------|---------|
| 1. Contrações obrigatórias | Universais que todo brasileiro faz | não é→né, para o→pro, estou→tô, está→tá |
| 2. R-drop verbos `-AR` | Apenas infinitivos -AR, com espaçamento 8 palavras | falar→falá, mandar→mandá, pagar→pagá |
| 3. Blacklist | Proibido: cê, num, purque, prum, pruma | Validação final remove se escapar |

**Ana (Sales Bot CRM — `wa_sales_bot.py`):**

Pipeline 9 etapas com detecção de contexto emocional:

| Etapa | Transformação |
|-------|--------------|
| 1. Contrações obrigatórias | não é→né, para o→pro, estou→tô, está→tá, estava→tava |
| 2. R-drop verbos -AR | falar→falá, explicar→explicá (espaçamento 8 palavras) |
| 3. Conectores informais | Inseridos 1 a cada 3 frases: "olha,", "tipo assim,", "sabe," |
| 4. Finalizadores | 1 a cada 4 frases: "entende?", "faz sentido?", "tá ligado?" |
| 5. Expressões congeladas | "Derekh Food", "por exemplo", "na verdade" — NUNCA modificar |
| 6. Detecção de contexto | sério/profissional/amigável/empolgado com limites de conversão |
| 7. Risadas → tags emoção | "haha", "rsrs" → `[risinhos]` |
| 8. Tags emoção Fish Audio | Adicionadas automaticamente: `[amigável]`, `[profissional]`, etc. |
| 9. Validação blacklist | Remove: cê, num, purque, prum, pruma |

**Limites por contexto:**

| Contexto | Max conversões | Keywords detectoras |
|----------|---------------|-------------------|
| sério | 1 | preço, valor, custo, contrato |
| profissional | 2 | empresa, solução, plataforma |
| amigável | 4 | show, legal, bacana, beleza |
| empolgado | 5 | incrível, demais, fantástico |

**Regra de espaçamento:** Máximo 1 conversão permitida a cada 8 palavras (anti-stacking).

**Arquivos modificados:**
- `backend/app/bot/atendente.py` — `_preparar_texto_para_audio()`, `_DICCAO_OBRIGATORIAS`, `_VERBOS_AR_DROP`
- `Hacking-restaurant-b2b/crm/wa_sales_bot.py` — `_preparar_texto_para_audio()` (pipeline 9 etapas)
- `Hacking-restaurant-b2b/crm/fish_tts.py` — `EMOTION_TAGS` atualizado

### 17.19 Correções Function Calls (27/03)

**`_validar_endereco` — Filtro por cidade e país:**
- Autocomplete Mapbox filtra pelo país do restaurante (`rest.pais`, ex: "BR", "PT")
- Após geocoding, filtra resultados pela cidade do restaurante
- Evita mostrar endereços de outros estados/países
- Se nenhum resultado na cidade: retorna mensagem pedindo endereço completo com bairro e cidade

**Geocoding multi-país (28/03):**
- Campo `pais` (ISO 2 letras) adicionado ao modelo Restaurante (default "BR")
- "Salvar e Geocodificar" detecta país automaticamente via Mapbox reverse geocoding
- Autocomplete (painel, site cliente, Bia) filtra pelo `country=rest.pais`
- Removido `country: "BR"` hardcoded de `geocode_address()` e `autocomplete_address()`

**Fix mensagens duplicadas bot (28/03):**
- Causa: 2 Gunicorn workers rodavam `_notificar_mudancas_status()` em paralelo (race condition)
- Fix: `SELECT FOR UPDATE SKIP LOCKED` na query de conversas (PostgreSQL)

**Fix URL tracking workers (28/03):**
- `workers.py` usava URL antiga `/pedido/{id}/tracking` → corrigido para `/order/{id}` com `BASE_URL`

**`_criar_pedido` — Bairro e distância no retorno:**
- Retorno JSON agora inclui `bairro_entrega` e `distancia_km`
- LLM usa esses dados para incluir na confirmação final: "Taxa R$X,XX (Bairro tal, X.Xkm)"

---

## 18. Repescagem Avançada + Verificação Email + Reset Senha (Migration 037)

### 18.1 Verificação de Email

Ao registrar conta no site, cliente recebe código OTP 6 dígitos por email (Resend).

**Fluxo:**
1. Cliente se registra com email → backend gera código 6 dígitos + salva em `clientes.codigo_verificacao` (validade 10min)
2. Email enviado em background via Resend com template visual (header gradient, código monoespaçado)
3. Frontend redireciona para `/verificar-email` — 6 inputs OTP com auto-advance, paste, countdown 10min
4. Reenvio disponível após 60s (rate limit via `verificacao_enviada_em` no BD)
5. Botão "Pular por agora" — verificação não é bloqueante
6. Sucesso → `email_verificado = True`, badge verde na conta

**Endpoints:**
| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| POST | `/auth/cliente/verificar-email` | JWT cliente | Valida código OTP |
| POST | `/auth/cliente/reenviar-verificacao` | JWT cliente | Reenvia código (cooldown 60s) |

### 18.2 Reset de Senha (Esqueci Minha Senha)

**Fluxo:**
1. Cliente clica "Esqueci minha senha" no login → navega para `/esqueci-senha`
2. Informa email → backend **sempre retorna 200** (segurança — não revela se email existe)
3. Se email existe: gera código 6 dígitos, salva em `clientes.codigo_reset_senha` (validade 10min), envia email
4. Frontend muda para estado 2: 6 inputs OTP + countdown 10min + nova senha + confirmar
5. Sucesso → senha atualizada com bcrypt, campos de reset limpos, redirect para `/login`

**Endpoints:**
| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| POST | `/auth/cliente/esqueci-senha` | Público | Envia código reset (sempre 200) |
| POST | `/auth/cliente/redefinir-senha` | Público | Valida código + redefine senha |
| POST | `/auth/cliente/alterar-senha` | JWT cliente | Altera senha (requer senha atual) |

### 18.3 Repescagem Avançada

Campanha de reativação de clientes inativos com cupons exclusivos personalizados.

**Formato do cupom:** `VOLTA-{PRIMEIRO_NOME}-{5chars_alfanuméricos}` (ex: `VOLTA-MARIO-A3K9F`)
- Código único por cliente, verificação de duplicidade no banco
- Vinculado a `Promoção` com `cliente_id` e `tipo_cupom='repescagem'`

**Envio em massa (Admin):**
1. Admin acessa aba "Repescagem" no Bot WhatsApp
2. Seleciona clientes inativos da lista (checkboxes)
3. Configura: desconto%, validade (dias), canal (WhatsApp/email/ambos)
4. Sistema cria Promoção exclusiva + BotRepescagem para cada cliente
5. Envia mensagem com cupom via canal escolhido

**Lembrete automático:**
- Worker verifica a cada ~1h cupons que expiram nas próximas 24h
- Envia lembrete via WA + email: "Seu cupom VOLTA-MARIO-A3K9F de 10% expira amanhã!"
- Marca `lembrete_enviado = True` para não repetir

**Cupons exclusivos no checkout:**
- Banner amarelo auto-sugerido acima do campo de cupom
- Clicável: preenche e valida automaticamente
- Validação de propriedade: cupom com `cliente_id` só pode ser usado pelo dono

**Cupons exclusivos no bot WA:**
- `buscar_promocoes` inclui cupons exclusivos do cliente na resposta
- `aplicar_cupom` verifica propriedade via `conversa.cliente_id`

**Endpoints:**
| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| POST | `/painel/bot/repescagem/criar-em-massa` | JWT restaurante | Envia repescagem para N clientes |
| GET | `/painel/bot/repescagem/historico` | JWT restaurante | Histórico paginado (20/página) |
| GET | `/{codigo_acesso}/meus-cupons` | JWT cliente | Lista cupons exclusivos ativos |

### 18.4 Migration 037

**Revisão:** `037_repescagem_verificacao_senha` (revises `036_bot_whatsapp_v2`)

**Alterações:**
- `clientes`: +6 colunas (codigo_verificacao, codigo_verificacao_expira, verificacao_enviada_em, codigo_reset_senha, codigo_reset_expira, reset_enviado_em)
- `promocoes`: +2 colunas (cliente_id FK → clientes, tipo_cupom) + índice parcial
- `bot_repescagens`: +6 colunas (cupom_validade_dias, lembrete_enviado, lembrete_enviado_em, canal, email_enviado, promocao_id FK → promocoes)

### 18.5 Arquivos do Módulo

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| `migrations/versions/037_repescagem_verificacao_senha.py` | Novo | Migration com IF EXISTS/IF NOT EXISTS |
| `database/models.py` | Modificado | +6 campos Cliente, +2 Promoção, +6 BotRepescagem |
| `backend/app/email_templates.py` | Modificado | +3 templates (verificação, reset, lembrete cupom) |
| `backend/app/email_service.py` | Modificado | +3 funções envio email |
| `backend/app/schemas/cliente_schemas.py` | Modificado | +4 schemas (verificar, esqueci, redefinir, alterar) |
| `backend/app/routers/auth_cliente.py` | Modificado | +5 endpoints auth + envio verificação no registro |
| `backend/app/routers/bot_whatsapp.py` | Modificado | +2 endpoints repescagem (massa + histórico) |
| `backend/app/routers/site_cliente.py` | Modificado | +1 endpoint meus-cupons, validação ownership |
| `backend/app/bot/workers.py` | Modificado | Worker lembrete cupom + repescagem com Promoção |
| `backend/app/bot/function_calls.py` | Modificado | Cupons exclusivos no bot (buscar + aplicar) |
| `client/src/lib/apiClient.ts` | Modificado | +7 funções API |
| `client/src/hooks/useQueries.ts` | Modificado | +7 hooks TanStack Query |
| `client/src/pages/VerificarEmail.tsx` | Novo | Página OTP 6 dígitos + countdown |
| `client/src/pages/EsqueciSenha.tsx` | Novo | Solicitar código + redefinir senha |
| `client/src/pages/Login.tsx` | Modificado | Link "Esqueci senha" + redirect verificação |
| `client/src/pages/Account.tsx` | Modificado | Badge verificado + alterar senha |
| `client/src/pages/Checkout.tsx` | Modificado | Banner cupons exclusivos auto-sugeridos |
| `client/src/App.tsx` | Modificado | +2 rotas (verificar-email, esqueci-senha) |
| `client/src/contexts/AuthContext.tsx` | Modificado | +email_verificado na interface |
| `client/src/admin/pages/BotWhatsApp.tsx` | Modificado | +aba Repescagem (lista + envio + histórico) |
| `client/src/admin/lib/adminApiClient.ts` | Modificado | +2 funções admin API |
| `client/src/admin/hooks/useAdminQueries.ts` | Modificado | +2 hooks |

---

## 19. Security Hardening (26/03/2026)

Auditoria de segurança completa com correção de 8 vulnerabilidades críticas e high.

### 19.1 Resumo das Correções

| # | Vulnerabilidade | Severidade | Correção |
|---|----------------|------------|----------|
| 1 | Evolution API expunha API keys publicamente | Crítica | `EXPOSE_IN_FETCH_INSTANCES = false` |
| 2 | `/metrics` acessível sem autenticação | High | Protegido com `Depends(get_current_admin)` |
| 3 | Webhook Evolution aceitava qualquer POST | High | Validação header `apikey` via `hmac.compare_digest` |
| 4 | SECRET_KEY com fallback hardcoded inseguro | High | Warning explícito + fallback dev-only separado |
| 5 | SECRET_KEY duplicada em auth_cliente.py | Média | Importação centralizada do `auth.py` |
| 6 | CORS permissivo (wildcard methods/headers) | Média | Origins explícitas + métodos/headers restritos |
| 7 | Ausência de security headers HTTP | Média | Middleware HSTS, X-Frame-Options, CSP, nosniff |
| 8 | Woovi webhook aceitava tudo sem secret | High | Rejeita em produção (`FLY_APP_NAME`) |
| 9 | OpenDelivery webhook com validação bypass | High | Assinatura obrigatória quando secret existe |

### 19.2 Security Headers

Todas as respostas HTTP agora incluem:
- `X-Content-Type-Options: nosniff` — previne MIME sniffing
- `X-Frame-Options: DENY` — previne clickjacking
- `X-XSS-Protection: 1; mode=block` — proteção XSS legacy
- `Referrer-Policy: strict-origin-when-cross-origin` — controle de referrer
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` — força HTTPS (exceto /docs)

### 19.3 CORS

Origins permitidas:
- `http://localhost:5173` (Vite dev)
- `http://localhost:3000` (React dev)
- `https://superfood-api.fly.dev` (produção)
- `https://derekhfood.com.br` e `https://www.derekhfood.com.br`
- `https://*.derekhfood.com.br` (subdomínios via regex)

Métodos: `GET, POST, PUT, PATCH, DELETE, OPTIONS` (não mais wildcard).
Headers: `Authorization, Content-Type, X-Requested-With` (não mais wildcard).

### 19.4 Webhook Evolution — Validação apikey

- Header `apikey` validado via `hmac.compare_digest` contra `EVOLUTION_WEBHOOK_SECRET`
- Secret configurado como variável de ambiente no Fly.io
- Sem secret configurado (dev local): aceita tudo para facilitar desenvolvimento

### 19.5 SECRET_KEY Centralizada

- `auth.py` é a source of truth para `SECRET_KEY` e `ALGORITHM`
- `auth_cliente.py` importa de `auth.py` (antes tinha fallback hardcoded próprio)
- Warning emitido se SECRET_KEY não está no ambiente (não crashar app em dev)

### 19.6 Testes de Segurança

36 testes automatizados em `tests/test_security_hardening.py`:
- Etapa 1: Evolution API expose (1 teste)
- Etapa 2: /metrics auth (3 testes)
- Etapa 3: Webhook Evolution apikey (4 testes)
- Etapa 4: SECRET_KEY validação (5 testes)
- Etapa 5: CORS configuração (7 testes)
- Etapa 6: Security headers (7 testes)
- Etapa 7: Woovi webhook produção (3 testes)
- Etapa 8: OpenDelivery webhook (1 teste)
- Integração geral (5 testes)

### 19.7 Arquivos Modificados

| Arquivo | Ação |
|---------|------|
| `evolution-api/fly.toml` | EXPOSE = false |
| `backend/app/main.py` | /metrics auth, CORS prod, security headers middleware |
| `backend/app/auth.py` | SECRET_KEY validação + warning |
| `backend/app/routers/bot_whatsapp.py` | Validação apikey webhook |
| `backend/app/routers/auth_cliente.py` | Import SECRET_KEY centralizado |
| `backend/app/routers/integracoes.py` | Assinatura webhook obrigatória |
| `backend/app/pix/woovi_client.py` | Rejeitar webhook sem secret em prod |
| `tests/test_security_hardening.py` | 36 testes automatizados |

### 19.8 Deploy — Secret Necessário

```bash
# Copiar AUTHENTICATION_API_KEY da Evolution para o backend
fly secrets set EVOLUTION_WEBHOOK_SECRET="<apikey-da-evolution>" --app superfood-api
```

---

*Documento gerado automaticamente pelo sistema Derekh Food v4.0.2*
*Última atualização: 27/03/2026*
*Para suporte técnico: contato@derekhfood.com.br*
*WhatsApp comercial: +1 555-900-4563*
