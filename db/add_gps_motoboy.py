from db.database import DBManager

db = DBManager()

try:
    db.cursor.execute("ALTER TABLE motoboys ADD COLUMN latitude REAL")
    db.cursor.execute("ALTER TABLE motoboys ADD COLUMN longitude REAL")
    db.conn.commit()
    print("Colunas latitude e longitude adicionadas em motoboys")
except:
    print("Colunas já existiam")

db.close()
