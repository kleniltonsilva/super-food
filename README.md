🍕 Super Food
Plataforma SaaS Multi-Restaurante (SOFTWARE PROPRIETÁRIO)
⚠️ AVISO DE LICENÇA — IMPORTANTE 🚫
ESTE REPOSITÓRIO NÃO É OPEN SOURCE

Este código-fonte é PROPRIETÁRIO E CONFIDENCIAL.

O código está disponível publicamente exclusivamente para fins de apresentação técnica e portfólio profissional.

NENHUM DIREITO É CONCEDIDO, incluindo, mas não se limitando a:

❌ Uso

❌ Cópia

❌ Reprodução

❌ Modificação

❌ Adaptação

❌ Estudo para implementação

❌ Distribuição

❌ Sublicenciamento

❌ Venda

❌ Criação de obras derivadas

Qualquer forma de reprodução, armazenamento, transmissão, execução ou exploração deste código — total ou parcial, por qualquer meio — é estritamente proibida sem autorização prévia, expressa e por escrito do titular dos direitos.

Violações podem resultar em responsabilização civil e criminal.

📄 Consulte o arquivo LICENSE para os termos legais completos.

📌 Sobre o Projeto

Super Food é uma plataforma SaaS proprietária para gestão inteligente de múltiplos restaurantes, com foco em:

Operações de delivery em escala

Despacho inteligente de entregas

Rastreamento GPS em tempo real

Gestão financeira e operacional

Arquitetura multi-tenant

📋 Índice

Visão Geral

Funcionalidades

Arquitetura

Instalação

Configuração

Como Usar

Estrutura de Dados

API Mapbox

Licença

🎯 Visão Geral

O Super Food é um sistema completo de gestão multi-restaurante, oferecendo:

👑 Painel Super Admin — controle global da plataforma

🏪 Dashboard do Restaurante — pedidos, motoboys e caixa

🏍️ App PWA do Motoboy — interface mobile-first

🗺️ Rastreamento GPS em tempo real

💰 Gestão Financeira — caixa, planos e pagamentos

📊 Relatórios e rankings operacionais

✨ Funcionalidades
👑 Super Admin

Criação e gerenciamento de restaurantes

Controle de planos e assinaturas

Métricas globais da plataforma

Gestão de pagamentos

🏪 Restaurante

Gestão de pedidos (Entrega, Retirada, Mesa)

Aprovação e gerenciamento de motoboys

Despacho inteligente (automático e manual)

Controle de caixa

Configurações operacionais

🏍️ App Motoboy (PWA)

Cadastro com código de acesso

Aprovação pelo restaurante

Recebimento de entregas

Envio de localização GPS em tempo real

Histórico de ganhos

🏗️ Arquitetura do Projeto
super-food/
├── app_motoboy/
│   └── motoboy_app.py
│
├── backend/
│   ├── app/
│   │   ├── auth.py
│   │   ├── database.py
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── middleware.py
│   │   ├── models.py
│   │   ├── routers/
│   │   │   ├── motoboys.py
│   │   │   ├── pedidos.py
│   │   │   └── restaurantes.py
│   │   ├── schemas.py
│   │   └── utils/
│   │       └── despacho.py
│   ├── app.py
│   └── __init__.py
│
├── database/
│   ├── base.py
│   ├── __init__.py
│   ├── migration_script.py
│   ├── models.py
│   ├── session.py
│   └── super_food.db
│
├── db/
│   ├── add_gps_motoboy.py
│   ├── add_motoboy_restaurante.py
│   ├── add_motoboy_to_pedidos.py
│   ├── add_restaurantes_table.py
│   ├── create_pedidos_table.py
│   ├── database.py
│   └── __init__.py
│
├── migrations/
│   ├── add_auth_columns_motoboys.py
│   ├── add_coords_restaurantes.py
│   ├── add_max_pedidos_motoboys.py
│   ├── add_missing_columns_to_restaurantes.py
│   └── add_tenant_id_multi_tenant.py
│
├── streamlit_app/
│   ├── __init__.py
│   ├── restaurante_app.py
│   └── super_admin.py
│
├── utils/
│   ├── haversine.py
│   ├── mapbox_api.py
│   └── __init__.py
│
├── Screenshots/
├── requirements.txt
├── README.md
├── LICENSE
├── DOC.md
└── super_food.db

🚀 Instalação

⚠️ Este projeto NÃO é licenciado para uso externo.
As instruções abaixo existem apenas para fins de documentação técnica.

Pré-requisitos

Python 3.9 ou superior

pip

Conta Mapbox

cd super-food

⚙️ Configuração

Exemplo meramente ilustrativo de arquivo .env:

MAPBOX_TOKEN=example_token
DATABASE_PATH=super_food.db
DEBUG=True

📖 Como Usar

⚠️ A execução, teste ou deploy por terceiros NÃO É AUTORIZADA.
Os comandos abaixo são exibidos apenas para documentação técnica:

streamlit run streamlit_app/super_admin.py
streamlit run streamlit_app/restaurante_app.py
streamlit run app_motoboy/motoboy_app.py

🗄️ Estrutura de Dados

Mais de 15 tabelas integradas

Restaurantes

Motoboys

Pedidos

Entregas

Caixa

Cache de rotas

Rankings

🗺️ API Mapbox

Geocoding

Cálculo de rotas

Cache inteligente de requisições

Economia de até 90% nas chamadas da API

📝 Licença

SOFTWARE PROPRIETÁRIO — TODOS OS DIREITOS RESERVADOS

Este software é proprietário e confidencial.
Nenhuma permissão é concedida para uso, cópia, modificação, redistribuição ou criação de obras derivadas sem autorização expressa e por escrito do autor.

Consulte o arquivo LICENSE para os termos completos.

👤 Autor

Klenilton Silva
GitHub: https://github.com/kleniltonsilva

📊 Status do Projeto

✔ Ativo

✔ Em desenvolvimento contínuo

✔ Uso comercial exclusivo do autor
