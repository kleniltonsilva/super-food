from db.database import DBManager

db = DBManager()

try:
    db.cursor.execute("ALTER TABLE restaurantes ADD COLUMN latitude REAL")
    db.cursor.execute("ALTER TABLE restaurantes ADD COLUMN longitude REAL")
    db.conn.commit()
    print("Colunas de coordenadas adicionadas em restaurantes")
except Exception as e:
    print("Já existiam ou erro:", e)

db.close()