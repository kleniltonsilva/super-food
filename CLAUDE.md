# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Super Food is a multi-tenant SaaS platform for restaurant management with real-time delivery tracking and route optimization. Built with Python 3.12+, Streamlit (frontend), SQLAlchemy 2.0+ ORM, and Alembic migrations.

## Common Commands

### Running Applications
```bash
# Activate virtual environment first
source venv/bin/activate

# Super Admin dashboard (port 8501)
streamlit run streamlit_app/super_admin.py

# Restaurant dashboard (port 8502)
streamlit run streamlit_app/restaurante_app.py --server.port=8502

# Motoboy PWA (port 8503)
streamlit run app_motoboy/motoboy_app.py --server.port=8503
```

### Database Operations
```bash
# Initialize database with default data
python init_database.py

# Apply all pending migrations
alembic upgrade head

# Revert last migration
alembic downgrade -1

# Generate new migration from model changes
alembic revision --autogenerate -m "description"
```

### Installation
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Architecture

### Multi-Tenant Design
- All database queries MUST filter by `restaurante_id` to ensure tenant isolation
- `SuperAdmin` manages all restaurants globally
- Each restaurant is an isolated tenant with its own motoboys, orders, products, and configuration

### Layer Structure
```
Streamlit Apps / FastAPI Routes
         |
    SQLAlchemy ORM (database/models.py)
         |
    Session Management (database/session.py)
         |
    Utility Services (utils/)
```

### Key Directories
- `database/` - SQLAlchemy ORM models and session management
- `migrations/` - Alembic migration scripts
- `streamlit_app/` - Super Admin and Restaurant dashboards
- `app_motoboy/` - Mobile-first PWA for delivery drivers
- `utils/` - Mapbox API integration, Haversine distance, TSP optimization
- `backend/` - FastAPI backend (in development)

### Database Models (16 tables)
Core models in `database/models.py`:
- `SuperAdmin`, `Restaurante`, `ConfigRestaurante` - Admin and tenant config
- `Motoboy`, `MotoboySolicitacao`, `GPSMotoboy` - Driver management and tracking
- `Pedido`, `Produto`, `CategoriaMenu`, `ItemPedido` - Orders and menu
- `Entrega`, `RotaOtimizada` - Delivery and route optimization
- `Caixa`, `MovimentacaoCaixa` - Financial management

### ORM Patterns
- Use `SessionLocal` from `database/session.py` for database sessions
- Always use eager loading (`joinedload()`) for relationships to avoid `DetachedInstanceError`
- Close sessions properly in Streamlit apps (use try/finally or context managers)

### External APIs
- **Mapbox**: Geocoding, routing, distance calculation (requires `MAPBOX_TOKEN` in `.env`)
- **Haversine**: Offline fallback for distance calculations
- **TSP Optimizer**: Nearest Neighbor algorithm for route optimization

## Configuration

Required `.env` variables:
```
MAPBOX_TOKEN=your_token_here
DATABASE_URL=sqlite:///./database/super_food.db
```

For PostgreSQL production:
```
DATABASE_URL=postgresql+psycopg2://user:pass@host/db
```

## Test Credentials
- Super Admin: `superadmin` / `SuperFood2025!`
- Test Restaurant: `teste@superfood.com` / `123456`

## Security Considerations
- Passwords use SHA256 hashing via `set_senha()` and `verificar_senha()` methods
- Access codes are auto-generated 8-character hex strings
- Multi-tenant isolation is enforced at the query level (always filter by `restaurante_id`)
