from db.database import DBManager

db = DBManager()

db.cursor.execute("""
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurante_id INTEGER,
        comanda TEXT,
        tipo TEXT,
        cliente_nome TEXT,
        cliente_telefone TEXT,
        endereco_entrega TEXT,
        numero_mesa TEXT,
        itens TEXT,
        observacoes TEXT,
        status TEXT DEFAULT 'novo',
        data_criacao TEXT,
        tempo_estimado INTEGER,
        FOREIGN KEY(restaurante_id) REFERENCES restaurantes(id)
    )
""")
db.conn.commit()
print("Tabela 'pedidos' criada com sucesso!")
db.close()
