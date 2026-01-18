import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "../super_food.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# motoboys
try:
    cursor.execute("ALTER TABLE motoboys ADD COLUMN capacidade_entregas INTEGER DEFAULT 3")
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE motoboys ADD COLUMN ultimo_status_online DATETIME")
except sqlite3.OperationalError:
    pass

# pedidos
try:
    cursor.execute("ALTER TABLE pedidos ADD COLUMN distancia_restaurante_km FLOAT DEFAULT 0")
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE pedidos ADD COLUMN ordem_rota INTEGER")
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE pedidos ADD COLUMN validado_mapbox BOOLEAN DEFAULT 0")
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE pedidos ADD COLUMN atrasado BOOLEAN DEFAULT 0")
except sqlite3.OperationalError:
    pass

conn.commit()
conn.close()
print("✅ Colunas novas adicionadas ao SQLite")
