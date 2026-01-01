from db.database import DBManager

db = DBManager()

# Cria tabela restaurantes se não existir
db.cursor.execute("""
    CREATE TABLE IF NOT EXISTS restaurantes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        endereco TEXT,
        plano TEXT DEFAULT 'basico',
        codigo_acesso TEXT UNIQUE,
        ativo INTEGER DEFAULT 1
    )
""")
db.conn.commit()

print("Tabela 'restaurantes' criada ou já existia.")
db.close()
