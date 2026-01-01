# arquivo: migrations/add_max_pedidos_motoboys.py
import sys
import os

# Adiciona a raiz do projeto ao path para que o import funcione de qualquer pasta
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.database import DBManager

db = DBManager()

try:
    db.cursor.execute("ALTER TABLE motoboys ADD COLUMN max_pedidos_concurrentes INTEGER DEFAULT 3")
    db.conn.commit()
    print("Coluna max_pedidos_concurrentes adicionada com sucesso (default = 3 para todos os motoboys existentes)")
except Exception as e:
    print("Coluna já existia ou erro:", e)

db.close()