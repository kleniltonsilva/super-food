# Super Food - SaaS de Gerenciamento Inteligente de Entregas para Restaurantes

**Super Food** é uma plataforma SaaS completa projetada para restaurantes que precisam gerenciar entregas de forma eficiente, escalável e em tempo real. O sistema suporta múltiplos restaurantes (multi-tenant), com isolamento total de dados, planos de assinatura e despacho inteligente de pedidos.

## Objetivos Principais

1. **Centralizar e otimizar o fluxo de entregas**  
   - Permitir que restaurantes cadastrem pedidos rapidamente (entrega, retirada ou mesa).
   - Atribuir pedidos automaticamente ao motoboy mais próximo/disponível (despacho inteligente baseado em localização GPS e carga atual).
   - Calcular rotas otimizadas e tempos estimados usando Mapbox.

2. **Oferecer visibilidade em tempo real**  
   - Dashboard do restaurante com mapa interativo (PyDeck + Mapbox) mostrando:
     - Localização do restaurante
     - Endereços dos pedidos pendentes
     - Posição GPS atual dos motoboys
   - Log de eventos realtime via WebSocket (atribuições, atualizações de status, GPS).

3. **Modelo SaaS multi-restaurante com planos**  
   - Super Admin cria e gerencia restaurantes (signup completo com geocodificação automática).
   - Cada restaurante tem login independente (email + senha, JWT).
   - Limites por plano:
     - Básico: até 3 motoboys
     - Médio: até 5 motoboys
     - Premium: até 12 motoboys

4. **Facilitar o cadastro e operação dos motoboys**  
   - Cadastro simplificado no dashboard do restaurante usando código de acesso único.
   - Futuro: PWA dedicada para motoboys (receber pedidos, atualizar GPS, confirmar entregas, visualizar ganhos por km).

5. **Segurança, escalabilidade e manutenção simples**  
   - Autenticação JWT segura (sem query params expostos).
   - Dados isolados por restaurante_id.
   - Uso de .env para tokens sensíveis (Mapbox, banco, etc.).
   - Backend FastAPI + SQLAlchemy, frontend Streamlit.

## Funcionalidades Atuais (Implementadas)

- **Super Admin** (`super_admin.py`)
  - Listar todos os restaurantes
  - Criar novo restaurante com geocodificação automática (Mapbox)
  - Geração automática de código de acesso para motoboys

- **Dashboard do Restaurante** (`restaurante_dashboard.py`)
  - Login seguro com email/senha
  - Exibição de informações do restaurante (plano, taxa, código de acesso)
  - Mapa realtime com restaurante, pedidos e motoboys
  - Log de eventos WebSocket
  - Criar pedidos (comanda sequencial automática, geocodificação futura)
  - Despacho automático ao criar pedido de entrega
  - Listar pedidos em andamento
  - Cadastrar motoboys (validação por código de acesso)
  - Respeito aos limites de motoboys por plano

- **Backend FastAPI**
  - Rotas protegidas por JWT (/me, /meus)
  - Endpoints para pedidos, motoboys, GPS
  - WebSocket realtime por restaurante
  - Signup e login de restaurantes

## Arquitetura Atual

gerenciador-motoboys/ ├── backend/ │   └── app/ │       ├── main.py │       ├── routers/ (restaurantes.py, pedidos.py, motoboys.py, etc.) │       ├── models/ │       ├── dependencies/ (auth JWT) │       └── websocket connections ├── streamlit_app/ │   ├── restaurante_dashboard.py    ← Dashboard completo + login integrado │   └── super_admin.py              ← Painel de administração ├── utils/ │   └── mapbox.py                   ← Funções de geocodificação ├── db/ │   └── database.py                 ← DBManager (SQLite temporário) ├── .env                            ← Tokens e configurações └── requirements.txt

## Tecnologias Utilizadas

- **Backend**: FastAPI, Uvicorn, SQLAlchemy, JWT (PyJWT), Passlib (bcrypt)
- **Frontend**: Streamlit, PyDeck (Mapbox integration)
- **Mapa/Rotas**: Mapbox GL (token via .env)
- **Realtime**: WebSocket nativo do FastAPI
- **Banco**: SQLite (em desenvolvimento – migração futura para PostgreSQL)

## Como Rodar Localmente

1. Clone o repositório e entre na pasta
2. Crie ambiente virtual: `python -m venv venv && source venv/bin/activate`
3. Instale dependências: `pip install -r requirements.txt`
4. Crie `.env` com `MAPBOX_TOKEN=pk.seu_token_aqui` (e outras vars se necessário)
5. Rode o backend: `uvicorn backend.app.main:app --reload`
6. Em outro terminal:
   - Super Admin: `streamlit run streamlit_app/super_admin.py`
   - Dashboard Restaurante: `streamlit run streamlit_app/restaurante_dashboard.py`

## Roadmap Futuro

- PWA completa para motoboys (notificações push, atualização GPS automática)
- Cálculo de ganhos por km e relatório financeiro
- Integração com gateways de pagamento (assinaturas SaaS)
- Migração para PostgreSQL + Alembic
- Otimização avançada de rotas (múltiplos pedidos por motoboy)
- Notificações WhatsApp/SMS para clientes

