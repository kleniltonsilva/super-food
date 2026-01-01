from db.database import DBManager

db = DBManager()

try:
    db.cursor.execute("ALTER TABLE pedidos ADD COLUMN motoboy_id INTEGER")
    db.cursor.execute("ALTER TABLE pedidos ADD COLUMN status TEXT DEFAULT 'novo'")
    db.conn.commit()
    print("Colunas motoboy_id e status adicionadas em pedidos")
except:
    print("Colunas já existiam ou tabela ainda não existe")

db.close()
