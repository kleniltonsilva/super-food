"""
Atualização manual do banco de dados (SEM ALEMBIC)

- Cria tabelas ausentes
- Adiciona colunas novas com segurança
- Cria índices se não existirem
- NÃO apaga dados
- Pode ser executado múltiplas vezes
"""

from sqlalchemy import inspect, text
from database.session import engine, get_db_session, init_db
from .models import Base


def column_exists(inspector, table_name, column_name):
    return column_name in [col["name"] for col in inspector.get_columns(table_name)]


def index_exists(inspector, table_name, index_name):
    return index_name in [idx["name"] for idx in inspector.get_indexes(table_name)]


def upgrade_database():
    inspector = inspect(engine)

    print("🔄 Atualizando banco de dados...")

    # 1️⃣ Cria tabelas que não existem
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:

        # ---------------- CONFIG_RESTAURANTE ----------------
        if "config_restaurante" in inspector.get_table_names():
            if not column_exists(inspector, "config_restaurante", "raio_entrega_km"):
                conn.execute(text(
                    "ALTER TABLE config_restaurante ADD COLUMN raio_entrega_km FLOAT DEFAULT 10.0"
                ))

            if not column_exists(inspector, "config_restaurante", "tempo_medio_preparo"):
                conn.execute(text(
                    "ALTER TABLE config_restaurante ADD COLUMN tempo_medio_preparo INTEGER DEFAULT 30"
                ))

            if not column_exists(inspector, "config_restaurante", "despacho_automatico"):
                conn.execute(text(
                    "ALTER TABLE config_restaurante ADD COLUMN despacho_automatico BOOLEAN DEFAULT 1"
                ))

        # ---------------- MOTOBOYS ----------------
        if "motoboys" in inspector.get_table_names():
            if not column_exists(inspector, "motoboys", "capacidade_entregas"):
                conn.execute(text(
                    "ALTER TABLE motoboys ADD COLUMN capacidade_entregas INTEGER DEFAULT 3"
                ))

            if not column_exists(inspector, "motoboys", "ultimo_status_online"):
                conn.execute(text(
                    "ALTER TABLE motoboys ADD COLUMN ultimo_status_online DATETIME"
                ))

        # ---------------- PEDIDOS ----------------
        if "pedidos" in inspector.get_table_names():
            if not column_exists(inspector, "pedidos", "distancia_restaurante_km"):
                conn.execute(text(
                    "ALTER TABLE pedidos ADD COLUMN distancia_restaurante_km FLOAT"
                ))

            if not column_exists(inspector, "pedidos", "ordem_rota"):
                conn.execute(text(
                    "ALTER TABLE pedidos ADD COLUMN ordem_rota INTEGER"
                ))

            if not column_exists(inspector, "pedidos", "validado_mapbox"):
                conn.execute(text(
                    "ALTER TABLE pedidos ADD COLUMN validado_mapbox BOOLEAN DEFAULT 0"
                ))

            if not column_exists(inspector, "pedidos", "atrasado"):
                conn.execute(text(
                    "ALTER TABLE pedidos ADD COLUMN atrasado BOOLEAN DEFAULT 0"
                ))

            if not index_exists(inspector, "pedidos", "idx_pedido_atrasado"):
                conn.execute(text(
                    "CREATE INDEX idx_pedido_atrasado ON pedidos (restaurante_id, atrasado)"
                ))

        # ---------------- ENTREGAS ----------------
        if "entregas" in inspector.get_table_names():
            if not column_exists(inspector, "entregas", "posicao_rota_original"):
                conn.execute(text(
                    "ALTER TABLE entregas ADD COLUMN posicao_rota_original INTEGER"
                ))

            if not column_exists(inspector, "entregas", "posicao_rota_otimizada"):
                conn.execute(text(
                    "ALTER TABLE entregas ADD COLUMN posicao_rota_otimizada INTEGER"
                ))

            if not column_exists(inspector, "entregas", "tempo_preparacao"):
                conn.execute(text(
                    "ALTER TABLE entregas ADD COLUMN tempo_preparacao INTEGER"
                ))

    print("✅ Banco atualizado com sucesso.")
