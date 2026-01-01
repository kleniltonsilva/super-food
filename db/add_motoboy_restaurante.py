from db.database import DBManager

db = DBManager()

# Adiciona coluna restaurante_id na tabela motoboys
try:
    db.cursor.execute("ALTER TABLE motoboys ADD COLUMN restaurante_id INTEGER")
    db.cursor.execute("ALTER TABLE motoboys ADD COLUMN status TEXT DEFAULT 'disponivel'")
    db.conn.commit()
    print("Colunas adicionadas em motoboys (restaurante_id e status)")
except:
    print("Colunas já existiam")

db.close()
