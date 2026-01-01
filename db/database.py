import sqlite3
import os
from datetime import datetime

class DBManager:
    def __init__(self, db_path="motoboys.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.alter_schema()

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY,
                diaria REAL DEFAULT 0,
                lanche REAL DEFAULT 0,
                taxa_entrega REAL DEFAULT 0,
                km_extra REAL DEFAULT 0,
                valor_km_extra REAL DEFAULT 0,
                endereco_restaurante TEXT DEFAULT ''
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS motoboys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                motoboy_id INTEGER,
                entregas INTEGER,
                taxa_total REAL,
                diaria REAL,
                lanche REAL,
                km_extra REAL,
                valor_extra REAL,
                total REAL,
                details TEXT,
                FOREIGN KEY(motoboy_id) REFERENCES motoboys(id)
            )
        """)
        # Insere configuração padrão se não existir
        self.cursor.execute("SELECT COUNT(*) FROM config")
        if self.cursor.fetchone()[0] == 0:
            self.cursor.execute("""
                INSERT INTO config (diaria, lanche, taxa_entrega, km_extra, valor_km_extra, endereco_restaurante)
                VALUES (0, 0, 0, 0, 0, '')
            """)
        self.conn.commit()

    def alter_schema(self):
        try:
            self.cursor.execute("ALTER TABLE results ADD COLUMN km_extra REAL DEFAULT 0")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            self.cursor.execute("ALTER TABLE results ADD COLUMN valor_extra REAL DEFAULT 0")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            self.cursor.execute("ALTER TABLE results ADD COLUMN details TEXT")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass

    # === Métodos do seu código original (copie todos) ===
    def get_config(self):
        self.cursor.execute("SELECT diaria, lanche, taxa_entrega, km_extra, valor_km_extra, endereco_restaurante FROM config WHERE id = 1")
        row = self.cursor.fetchone()
        if row:
            return {
                'diaria': row[0],
                'lanche': row[1],
                'taxa_entrega': row[2],
                'km_extra': row[3],
                'valor_km_extra': row[4],
                'endereco_restaurante': row[5]
            }
        return {'diaria': 0, 'lanche': 0, 'taxa_entrega': 0, 'km_extra': 0, 'valor_km_extra': 0, 'endereco_restaurante': ''}

    def save_config(self, config):
        self.cursor.execute("""
            UPDATE config SET diaria = ?, lanche = ?, taxa_entrega = ?, km_extra = ?, valor_km_extra = ?, endereco_restaurante = ?
            WHERE id = 1
        """, (config['diaria'], config['lanche'], config['taxa_entrega'], config['km_extra'], config['valor_km_extra'], config['endereco_restaurante']))
        self.conn.commit()

    def add_motoboy(self, nome):
        self.cursor.execute("INSERT INTO motoboys (nome) VALUES (?)", (nome,))
        self.conn.commit()

    def delete_motoboy(self, motoboy_id):
        self.cursor.execute("DELETE FROM motoboys WHERE id = ?", (motoboy_id,))
        self.conn.commit()

    def get_motoboys(self):
        self.cursor.execute("SELECT id, nome FROM motoboys ORDER BY nome")
        return self.cursor.fetchall()

    def save_payment_result(self, data, motoboy_id, entregas, taxa_total, diaria, lanche, km_extra, valor_extra, total, details):
        self.cursor.execute("""
            INSERT INTO results (data, motoboy_id, entregas, taxa_total, diaria, lanche, km_extra, valor_extra, total, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (data, motoboy_id, entregas, taxa_total, diaria, lanche, km_extra, valor_extra, total, details))
        self.conn.commit()

    def get_results_by_date(self, data):
        self.cursor.execute("""
            SELECT r.id, m.nome, r.entregas, r.taxa_total, r.diaria, r.lanche, r.km_extra, r.valor_extra, r.total, r.details
            FROM results r JOIN motoboys m ON r.motoboy_id = m.id
            WHERE r.data = ? ORDER BY m.nome
        """, (data,))
        return self.cursor.fetchall()

    def search_by_comanda(self, comanda):
        self.cursor.execute("""
            SELECT r.data, m.nome, r.details FROM results r
            JOIN motoboys m ON r.motoboy_id = m.id
            WHERE r.details LIKE ? 
        """, (f"%{comanda}%",))
        return self.cursor.fetchall()

    def get_ranking(self):
        self.cursor.execute("""
            SELECT m.nome, COUNT(r.id) as total_entregas, SUM(r.total) as total_ganho
            FROM results r JOIN motoboys m ON r.motoboy_id = m.id
            GROUP BY m.id ORDER BY total_entregas DESC
        """)
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()
