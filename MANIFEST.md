🍕 SUPER FOOD - PROJETO MANIFESTO  
Versão: 2.6  
Última Atualização: 18/01/2026  
Autor: Klenilton Silva  
Repositório: https://github.com/kleniltonsilva/super-food  

📋 VISÃO GERAL DO PROJETO  
Super Food é um sistema SaaS multi-tenant para gestão de restaurantes com:  

* 👑 Painel Super Admin (gerência de todos os restaurantes)  
* 🏪 Dashboard Restaurante (pedidos, motoboys, caixa)  
* 🏍️ PWA Motoboy (aplicativo com foco em dispositivos móveis)  
* 🗺️ Integração Mapbox (rotas, GPS, geocodificação)  
* 💰 Gestão Financeira (planos, assinaturas, caixa)  

🏗️ ARQUITETURA TÉCNICA  
Princípio da Pilha:  

* Backend: Python 3.12+  
* Banco de Dados: SQLite (dev) → PostgreSQL (prod)  
* ORM: SQLAlchemy 2.0+  
* Frontend: Streamlit 1.40+  
* API Externa: Mapbox (geocodificação, rotas)  
* Migrações: Alembic 1.18+ (configuração completa e funcional)  

Sistema de banco de dados:  
Unificado em SQLAlchemy ORM (database/models.py + migrations/).  
Legado SQLite raw (database.py) removido ou obsoleto.  
Todos apps (super_admin.py, restaurante_app.py, motoboy_app.py) usam ORM puro.  

📁 ESTRUTURA DE ARQUIVOS (atual em 18/01/2026)
super-food/
│
├── 📄 alembic.ini                      # Configuração Alembic (completa)
├── 🔑 .env                             # Variáveis de ambiente
├── 📦 requirements.txt                 # Dependências Python
├── 📖 README.md                        # Documentação
├── 📜 LICENSE                          # Licença proprietária
├── 🖼️ logo.png                         # Logo do projeto
├── 🖼️ foto.png                         # Imagem ilustrativa
│
├── 📂 database/                        # SQLAlchemy ORM (único)
│   ├── init.py
│   ├── base.py                        # Base declarativa
│   ├── models.py                      # Models (16 tabelas + GPSMotoboy)
│   └── session.py                     # Session factory
│
├── 📂 migrations/                      # Alembic (funcional)
│   ├── env.py                         # Ambiente com models carregados
│   ├── script.py.mako                 # Template padrão
│   └── versions/                      # Todas migrations
│       ├── 001_initial_schema.py
│       └── 002_add_gps_motoboys_table.py
│
├── 📂 streamlit_app/                   # Apps Streamlit
│   ├── init.py
│   ├── super_admin.py                 # 👑 Painel Super Admin (ORM)
│   └── restaurante_app.py             # 🏪 Dashboard Restaurante (ORM)
│
├── 📂 app_motoboy/                     # PWA Motoboy
│   └── motoboy_app.py                 # 🏍️ Interface motoboy (ORM completo)
│
├── 📂 utils/                           # Utilitários
│   ├── init.py
│   ├── mapbox_api.py                  # Integração Mapbox
│   └── haversine.py                   # Cálculo distância
│
└── 📂 backend/ (FUTURO)                # FastAPI (opcional)
text🗄️ ESTRUTURA DO BANCO DE DADOS  
16 Tabelas Principais (atualizado):  
1. super_admin  
2. restaurantes  
3. config_restaurante  
4. motoboys  
5. motoboys_solicitacoes  
6. produtos  
7. pedidos  
8. itens_pedido  
9. entregas  
10. rotas_otimizadas  
11. caixa  
12. movimentacoes_caixa  
13. notificacoes  
14. gps_motoboys (criada via migration 002)  
15. ranking_motoboys (se mantida)  
16. assinaturas (se mantida)  

🔧 FUNCIONALIDADES PRINCIPAIS  
👑 SUPER ADMINISTRADOR (super_admin.py)  
✅ Login seguro (SHA256)  
✅ Criar restaurantes  
✅ Gerenciar planos  
✅ Renovar assinaturas  
✅ Dashboard global  

🏪 RESTAURANTE (restaurante_app.py)  
✅ Login  
✅ Criar/gerenciar pedidos  
✅ Despacho automático/inteligente  
✅ Gerenciar motoboys  
✅ Caixa e movimentações  
✅ Configurações  

🏍️ MOTOBOY (motoboy_app.py)  
✅ Cadastro via código  
✅ Login após aprovação  
✅ Atualização GPS (tabela + ORM)  
✅ Receber entregas otimizadas  
✅ Histórico ganhos/perfil  

🗺️ MAPBOX + GPS  
✅ Geocoding + rotas  
✅ Cache inteligente  
✅ Histórico GPS em gps_motoboys  
✅ Eager loading em relacionamentos  

🔐 SEGURANÇA  
* Senhas: SHA256  
* Multi-tenant: restaurante_id em todas queries  
* Código acesso: gerado automaticamente  
* .env para chaves  

📊 PLANOS E LIMITES  
(manter tabela existente no seu manifesto)  

🚀 COMO EXECUTAR  
```bash
# Ativar venv
source venv/bin/activate

# Instalar dependências (se necessário)
pip install -r requirements.txt

# Configurar .env
# MAPBOX_TOKEN=...

# Rodar apps
streamlit run streamlit_app/super_admin.py
streamlit run streamlit_app/restaurante_app.py
streamlit run app_motoboy/motoboy_app.py
Credenciais padrão:

Superadmin: superadmin / SuperFood2025!
Restaurante teste: teste@superfood.com / 123456

🎯 MODO DE DESPACHO
(manter descrição existente)
🔄 FLUXOS PRINCIPAIS
(manter fluxos existentes – agora com ORM unificado)
📝 NOTAS IMPORTANTES

Banco unificado SQLAlchemy ORM + Alembic funcional
Legado SQLite raw removido/obsoleto
Multi-tenant rigoroso (restaurante_id obrigatório)
GPS histórico completo (tabela + model)

🐛 QUESTÕES RESOLVIDAS

Banco duplo → unificado
DetachedInstanceError → corrigido com joinedload
Tabela gps_motoboys ausente → criada via migration 002
Alembic não configurado → ini, env.py, script.mako completos

🔮 ROTEIRO (FUTURO)
Fase 1: Rotas Inteligentes com IA (em progresso)
Fase 2: Backend FastAPI completo
Fase 3: Site do Cliente + rastreamento
Fase 4: Integração iFood
📧 CONTATO
Autor: Klenilton Silva
GitHub: https://github.com/kleniltonsilva
⚖️ LICENÇA
SOFTWARE PROPRIETÁRIO — TODOS OS DIREITOS RESERVADOS
🍕 Super Food - Sistema SaaS Multi-Restaurante
Última atualização: 18/01/2026
