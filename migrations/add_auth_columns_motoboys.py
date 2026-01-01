from db.database import DBManager

db = DBManager()

try:
    db.cursor.execute("ALTER TABLE motoboys ADD COLUMN sobrenome TEXT")
    db.cursor.execute("ALTER TABLE motoboys ADD COLUMN username TEXT UNIQUE")
    db.cursor.execute("ALTER TABLE motoboys ADD COLUMN senha_hash TEXT")
    db.conn.commit()
    print("Colunas de autenticação adicionadas")
except Exception as e:
    print("Já existiam ou erro:", e)

db.close()