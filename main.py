import os
os.environ['PYPPETEER_DISABLE_SIGNALS'] = 'true'

import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import re
from urllib.parse import quote
import sqlite3
from datetime import datetime
import random
import time
import requests

# Token secreto do Mapbox para uso no projeto
MAPBOX_TOKEN = "sk.eyJ1Ijoia2xlbmlsdG9uIiwiYSI6ImNtN24zZTkwNzBtb2oyanM2cThhbm4ydjMifQ.Z31v3U6kcngSJgmFkPrpRQ"

# --- Integração com Mapbox ---
def geocode(address):
    """
    Converte um endereço em coordenadas (longitude, latitude) usando a API de Geocodificação do Mapbox.
    """
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{quote(address)}.json"
    params = {
        "access_token": MAPBOX_TOKEN,
        "limit": 1
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        features = data.get("features")
        if features and len(features) > 0:
            # Retorna as coordenadas no formato [longitude, latitude]
            coords = features[0]["center"]
            return coords
        else:
            print(f"[ERRO] Nenhuma coordenada encontrada para: {address}")
            return None
    except Exception as e:
        print(f"[ERRO] Erro na geocodificação de '{address}': {e}")
        return None

def get_directions(origin_coords, dest_coords):
    """
    Obtém as direções (rota) entre duas coordenadas via Mapbox Directions API.
    """
    coordinates = f"{origin_coords[0]},{origin_coords[1]};{dest_coords[0]},{dest_coords[1]}"
    url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{coordinates}.json"
    params = {
         "access_token": MAPBOX_TOKEN,
         "geometries": "geojson",
         "overview": "full"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        routes = data.get("routes")
        if routes and len(routes) > 0:
            return routes[0]  # Retorna a primeira rota encontrada
        else:
            print("[ERRO] Nenhuma rota encontrada.")
            return None
    except Exception as e:
        print(f"[ERRO] Erro ao obter direções: {e}")
        return None

def calculate_distance_and_time(address_a, address_b):
    """
    Calcula a distância e o tempo estimado entre dois endereços.
    
    Passos:
      1. Converte o endereço A (restaurante) em coordenadas.
      2. Converte o endereço B (destino da entrega) em coordenadas.
      3. Obtém a rota entre as coordenadas via Mapbox.
      4. Retorna a distância em km e o tempo estimado em minutos.
    """
    coords_a = geocode(address_a)
    coords_b = geocode(address_b)
    if coords_a is None or coords_b is None:
        print("Falha na obtenção das coordenadas.")
        return None, None
    route = get_directions(coords_a, coords_b)
    if route is None:
        print("Falha na obtenção da rota.")
        return None, None
    distance_m = route.get("distance", 0)
    duration_s = route.get("duration", 0)
    distance_km = distance_m / 1000.0
    duration_min = duration_s / 60.0
    return round(distance_km, 2), round(duration_min, 2)

# --- Gerenciador do Banco de Dados ---
class DBManager:
    def __init__(self, db_name="motoboy.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.create_db_if_not_exists()
        self.alter_schema()

    def create_db_if_not_exists(self):
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("""
            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY,
                daily_rate REAL,
                lanche_value REAL,
                base_delivery_fee REAL,
                distance_threshold REAL,
                extra_rate REAL,
                restaurant_address TEXT
            )
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS motoboys (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE
            )
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY,
                motoboy_name TEXT,
                result REAL,
                date TEXT,
                details TEXT,
                deliveries INTEGER DEFAULT 0,
                taxas REAL DEFAULT 0
            )
            """)

    def alter_schema(self):
        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(config)")
        cols = [row[1] for row in cur.fetchall()]
        if "restaurant_address" not in cols:
            try:
                cur.execute("ALTER TABLE config ADD COLUMN restaurant_address TEXT")
            except Exception as e:
                print(f"[DEBUG] Erro ao alterar tabela config: {e}")
        cur.execute("PRAGMA table_info(results)")
        cols = [row[1] for row in cur.fetchall()]
        if "deliveries" not in cols:
            try:
                cur.execute("ALTER TABLE results ADD COLUMN deliveries INTEGER DEFAULT 0")
            except Exception as e:
                print(f"[DEBUG] Erro ao alterar tabela results (deliveries): {e}")
        cur.execute("PRAGMA table_info(results)")
        cols = [row[1] for row in cur.fetchall()]
        if "taxas" not in cols:
            try:
                cur.execute("ALTER TABLE results ADD COLUMN taxas REAL DEFAULT 0")
            except Exception as e:
                print(f"[DEBUG] Erro ao alterar tabela results (taxas): {e}")
        self.conn.commit()

    def save_config(self, restaurant_address, daily_rate, lanche_value, base_delivery_fee, distance_threshold, extra_rate):
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("SELECT id FROM config LIMIT 1")
            row = cur.fetchone()
            if row:
                cur.execute("""
                UPDATE config 
                SET restaurant_address=?, daily_rate=?, lanche_value=?, base_delivery_fee=?, distance_threshold=?, extra_rate=?
                WHERE id=?
                """, (restaurant_address, daily_rate, lanche_value, base_delivery_fee, distance_threshold, extra_rate, row[0]))
            else:
                cur.execute("""
                INSERT INTO config (restaurant_address, daily_rate, lanche_value, base_delivery_fee, distance_threshold, extra_rate)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (restaurant_address, daily_rate, lanche_value, base_delivery_fee, distance_threshold, extra_rate))

    def load_config(self):
        cur = self.conn.cursor()
        cur.execute("SELECT restaurant_address, daily_rate, lanche_value, base_delivery_fee, distance_threshold, extra_rate FROM config LIMIT 1")
        row = cur.fetchone()
        return row if row else None

    def save_motoboy(self, name):
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("INSERT OR IGNORE INTO motoboys (name) VALUES (?)", (name,))

    def delete_motoboy(self, name):
        with self.conn:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM motoboys WHERE name=?", (name,))

    def load_all_motoboys(self):
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM motoboys")
        rows = cur.fetchall()
        return [row[0] for row in rows]

    def save_result(self, motoboy_name, result, deliveries, taxas, details):
        with self.conn:
            cur = self.conn.cursor()
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("""
            INSERT INTO results (motoboy_name, result, deliveries, taxas, date, details)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (motoboy_name, result, deliveries, taxas, date_str, details))

    def search_results_by_date(self, date_str, comanda=None):
        cur = self.conn.cursor()
        if comanda:
            query = "SELECT motoboy_name, result, deliveries, date, details FROM results WHERE date LIKE ? AND details LIKE ?"
            cur.execute(query, (date_str + "%", f"%Código: {comanda}%"))
        else:
            query = "SELECT motoboy_name, result, deliveries, date, details FROM results WHERE date LIKE ?"
            cur.execute(query, (date_str + "%",))
        return cur.fetchall()

    def get_ranking(self):
        cur = self.conn.cursor()
        query = """
        SELECT motoboy_name, SUM(deliveries) as total_deliveries, SUM(taxas) as total_taxas, SUM(result) as total_final
        FROM results
        GROUP BY motoboy_name
        ORDER BY total_deliveries DESC
        LIMIT 50
        """
        cur.execute(query)
        return cur.fetchall()

# --- Aplicação Principal ---
class App:
    def __init__(self, master):
        self.master = master
        self.master.configure(bg="black")
        master.title("Calculadora de Pagamento - Motoboys")
        self.db = DBManager()
        default_address = "R. Pedro Claudino da Rocha, 96 - Sítio Cercado, Curitiba - PR, 81900-220, Brasil"
        config = self.db.load_config()
        if config:
            self.localizacao_atual = config[0]
            self.daily_rate = config[1]
            self.lanche_value = config[2]
            self.base_delivery_fee = config[3]
            self.distance_threshold = config[4]
            self.extra_rate = config[5]
        else:
            self.localizacao_atual = default_address
            self.daily_rate = 35.0
            self.lanche_value = 15.0
            self.base_delivery_fee = 5.0
            self.distance_threshold = 4.0
            self.extra_rate = 1.5
            self.db.save_config(default_address, self.daily_rate, self.lanche_value, self.base_delivery_fee, self.distance_threshold, self.extra_rate)
        self.motoboy_names = []
        self.motoboys_data = []  # Cada item: {"name": ..., "enderecos": [{"endereco": ..., "comanda": ...}, ...], "entrega_info": []}
        self.current_motoboy = 0
        self.current_entrega = 0
        self.frame = tk.Frame(master, bg="black")
        self.frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.modo_execucao = False
        self.route_cache = {}
        self.criar_tela_inicial()

    def criar_tela_inicial(self):
        for widget in self.frame.winfo_children():
            widget.destroy()
        canvas = tk.Canvas(self.frame, width=500, height=50, bg="black", highlightthickness=0)
        canvas.create_text(253, 28, text="Gerenciador de Motoboys", font=("Arial", 18, "bold"), fill="gray")
        canvas.create_text(250, 25, text="Gerenciador de Motoboys", font=("Arial", 18, "bold"), fill="white")
        canvas.pack(pady=10)
        try:
            # Obtém o caminho correto para a imagem, mesmo após a conversão para .exe
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            IMG_PATH = os.path.join(BASE_DIR, "foto.png")
            logo = tk.PhotoImage(file=IMG_PATH)
            logo_label = tk.Label(self.frame, image=logo, bg="black")
            logo_label.image = logo
            logo_label.pack(pady=10)
        except Exception as e:
            print(f"[ERRO] Não foi possível carregar a imagem: {e}")
        tk.Button(self.frame, text="Cadastrar Motoboys", width=20, command=self.criar_tela_cadastrar_motoboys,
                  fg="blue", activebackground="red").pack(pady=5)
        tk.Button(self.frame, text="Excluir Motoboy", width=20, command=self.selecionar_motoboy_para_exclusao,
                  fg="blue", activebackground="red").pack(pady=5)
        tk.Button(self.frame, text="Pagar Motoboys", width=20, command=self.criar_tela_selecionar_motoboys,
                  fg="blue", activebackground="red").pack(pady=5)
        tk.Button(self.frame, text="Consultar Dados", width=20, command=self.criar_tela_pesquisa,
                  fg="blue", activebackground="red").pack(pady=5)
        tk.Button(self.frame, text="Ranking de Motoboys", width=20, command=self.exibir_ranking,
                  fg="blue", activebackground="red").pack(pady=5)

    def selecionar_motoboy_para_exclusao(self):
        nomes = self.db.load_all_motoboys()
        if not nomes:
            messagebox.showinfo("Informação", "Nenhum motoboy cadastrado.")
            return
        win = tk.Toplevel(self.master)
        win.configure(bg="black")
        win.title("Excluir Motoboy")
        tk.Label(win, text="Selecione o motoboy a excluir:", font=("Arial", 12, "bold"), bg="black", fg="white").pack(pady=5)
        lb_frame = tk.Frame(win, bg="black")
        lb_frame.pack(pady=5)
        scrollbar = tk.Scrollbar(lb_frame, orient="vertical")
        lb = tk.Listbox(lb_frame, selectmode=tk.SINGLE, width=40, height=10, yscrollcommand=scrollbar.set,
                        bg="white", fg="blue")
        scrollbar.config(command=lb.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        lb.pack(side=tk.LEFT, fill=tk.BOTH)
        for nome in nomes:
            lb.insert(tk.END, nome)
        tk.Button(win, text="Excluir", command=lambda: self._confirmar_exclusao(lb, win),
                  fg="blue", activebackground="red", bg="lightgray").pack(pady=5)
        tk.Button(win, text="Cancelar", command=win.destroy,
                  fg="blue", activebackground="red", bg="lightgray").pack(pady=5)

    def _confirmar_exclusao(self, lb, win):
        idx = lb.curselection()
        if idx:
            nome_excluir = lb.get(idx[0])
            self.db.delete_motoboy(nome_excluir)
            messagebox.showinfo("Sucesso", f"Motoboy '{nome_excluir}' excluído com sucesso.")
            win.destroy()
            self.criar_tela_inicial()
        else:
            messagebox.showerror("Erro", "Selecione um motoboy.")

    def criar_tela_pesquisa(self):
        for widget in self.frame.winfo_children():
            widget.destroy()
        tk.Label(self.frame, text="Pesquisar Resultados", font=("Arial", 14, "bold"), bg="black", fg="white").pack(pady=5)
        search_frame = tk.Frame(self.frame, bg="black")
        search_frame.pack(pady=5)
        tk.Label(search_frame, text="Data (YYYY-MM-DD):", bg="black", fg="white").grid(row=0, column=0)
        self.data_entry = tk.Entry(search_frame, width=15)
        self.data_entry.grid(row=0, column=1, padx=5)
        tk.Label(search_frame, text="Código da Comanda:", bg="black", fg="white").grid(row=0, column=2)
        self.comanda_search_entry = tk.Entry(search_frame, width=10)
        self.comanda_search_entry.grid(row=0, column=3, padx=5)
        tk.Button(self.frame, text="Pesquisar", command=self.pesquisar_resultados,
                  fg="blue", activebackground="red", bg="lightgray").pack(pady=5)
        tk.Button(self.frame, text="Voltar", command=self.criar_tela_inicial,
                  fg="blue", activebackground="red", bg="lightgray").pack(pady=5)

    def pesquisar_resultados(self):
        data_str = self.data_entry.get().strip()
        comanda = self.comanda_search_entry.get().strip()
        if not data_str:
            messagebox.showerror("Erro", "Informe a data para pesquisa.")
            return
        results = self.db.search_results_by_date(data_str, comanda if comanda else None)
        if not results:
            messagebox.showinfo("Pesquisa", "Nenhum resultado encontrado para essa data/código.")
            return
        win = tk.Toplevel(self.master)
        win.configure(bg="black")
        win.title(f"Resultados de {data_str} (Código: {comanda if comanda else 'Todos'})")
        tree_frame = tk.Frame(win, bg="black")
        tree_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(tree_frame, orient="vertical")
        tree = ttk.Treeview(tree_frame, columns=("Motoboy", "Resultado", "Entregas", "Data", "Detalhes"),
                            show="headings", height=10, yscrollcommand=scrollbar.set)
        scrollbar.config(command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for col in ("Motoboy", "Resultado", "Entregas", "Data", "Detalhes"):
            tree.heading(col, text=col)
            tree.column(col, width=300, anchor="center")
        for row in results:
            tree.insert("", "end", values=row)
        tk.Button(win, text="Fechar", command=win.destroy,
                  fg="blue", activebackground="red", bg="lightgray").pack(pady=5)

    def criar_tela_cadastrar_motoboys(self):
        for widget in self.frame.winfo_children():
            widget.destroy()
        tk.Label(self.frame, text="Cadastro de Motoboys", font=("Arial", 14, "bold"), bg="black", fg="white").pack(pady=5)
        tk.Label(self.frame, text="Nome do Motoboy:", bg="black", fg="white").pack()
        self.nome_entry = tk.Entry(self.frame, width=30)
        self.nome_entry.pack()
        btn_frame = tk.Frame(self.frame, bg="black")
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Adicionar", command=self.adicionar_motoboy,
                  fg="blue", activebackground="red", bg="lightgray").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Excluir", command=self.excluir_motoboy,
                  fg="blue", activebackground="red", bg="lightgray").pack(side=tk.LEFT, padx=5)
        tk.Label(self.frame, text="Motoboys Cadastrados:", bg="black", fg="white").pack()
        lb_frame = tk.Frame(self.frame, bg="black")
        lb_frame.pack(pady=5)
        scrollbar = tk.Scrollbar(lb_frame, orient="vertical")
        self.lista_box = tk.Listbox(lb_frame, width=40, height=5, yscrollcommand=scrollbar.set,
                                    bg="white", fg="blue")
        scrollbar.config(command=self.lista_box.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.lista_box.pack(side=tk.LEFT, fill=tk.BOTH)
        tk.Button(self.frame, text="Concluir Cadastro", command=self.criar_tela_inicial,
                  fg="blue", activebackground="red", bg="lightgray").pack(pady=10)

    def adicionar_motoboy(self):
        nome = self.nome_entry.get().strip()
        if not nome:
            messagebox.showerror("Erro", "Nome não pode ser vazio.")
            return
        if nome in self.db.load_all_motoboys():
            messagebox.showerror("Erro", "Motoboy já cadastrado no sistema.")
            return
        self.motoboy_names.append(nome)
        self.db.save_motoboy(nome)
        self.lista_box.insert(tk.END, nome)
        self.nome_entry.delete(0, tk.END)

    def excluir_motoboy(self):
        nomes = self.db.load_all_motoboys()
        if not nomes:
            messagebox.showinfo("Informação", "Nenhum motoboy cadastrado.")
            return
        win = tk.Toplevel(self.master)
        win.configure(bg="black")
        win.title("Excluir Motoboy")
        tk.Label(win, text="Selecione o motoboy a excluir:", font=("Arial", 12, "bold"), bg="black", fg="white").pack(pady=5)
        lb_frame = tk.Frame(win, bg="black")
        lb_frame.pack(pady=5)
        scrollbar = tk.Scrollbar(lb_frame, orient="vertical")
        lb = tk.Listbox(lb_frame, selectmode=tk.SINGLE, width=40, height=10, yscrollcommand=scrollbar.set,
                        bg="white", fg="blue")
        scrollbar.config(command=lb.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        lb.pack(side=tk.LEFT, fill=tk.BOTH)
        for nome in nomes:
            lb.insert(tk.END, nome)
        tk.Button(win, text="Excluir", command=lambda: self._confirmar_exclusao(lb, win),
                  fg="blue", activebackground="red", bg="lightgray").pack(pady=5)
        tk.Button(win, text="Cancelar", command=win.destroy,
                  fg="blue", activebackground="red", bg="lightgray").pack(pady=5)

    def criar_tela_selecionar_motoboys(self):
        for widget in self.frame.winfo_children():
            widget.destroy()
        self.modo_execucao = True
        tk.Label(self.frame, text="Selecione os Motoboys para Pagamento", font=("Arial", 14, "bold"),
                 bg="black", fg="white").pack(pady=5)
        motoboys = self.db.load_all_motoboys()
        if not motoboys:
            messagebox.showinfo("Informação", "Nenhum motoboy cadastrado. Cadastre agora.")
            self.criar_tela_cadastrar_motoboys()
            return
        lb_frame = tk.Frame(self.frame, bg="black")
        lb_frame.pack(pady=5)
        scrollbar = tk.Scrollbar(lb_frame, orient="vertical")
        self.lista_multi = tk.Listbox(lb_frame, selectmode=tk.MULTIPLE, width=40, height=10, yscrollcommand=scrollbar.set,
                                      bg="white", fg="blue")
        scrollbar.config(command=self.lista_multi.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.lista_multi.pack(side=tk.LEFT, fill=tk.BOTH)
        for mb in motoboys:
            self.lista_multi.insert(tk.END, mb)
        tk.Button(self.frame, text="Adicionar Novo Motoboy", command=self.criar_tela_cadastrar_motoboys,
                  fg="blue", activebackground="red", bg="lightgray").pack(pady=5)
        tk.Button(self.frame, text="Confirmar Seleção", command=self.confirmar_selecao_motoboys,
                  fg="blue", activebackground="red", bg="lightgray").pack(pady=5)
        tk.Button(self.frame, text="Voltar", command=self.criar_tela_inicial,
                  fg="blue", activebackground="red", bg="lightgray").pack(pady=5)

    def confirmar_selecao_motoboys(self):
        selecionados = self.lista_multi.curselection()
        if not selecionados:
            messagebox.showerror("Erro", "Selecione pelo menos um motoboy.")
            return
        self.motoboy_names = [self.lista_multi.get(i) for i in selecionados]
        self.motoboys_data = [{"name": name, "enderecos": [], "entrega_info": []} for name in self.motoboy_names]
        self.current_motoboy = 0
        self.criar_tela_configuracao()

    def criar_tela_configuracao(self):
        for widget in self.frame.winfo_children():
            widget.destroy()
        tk.Label(self.frame, text="Configuração do Sistema", font=("Arial", 14, "bold"),
                 bg="black", fg="white").pack(pady=5)
        tk.Label(self.frame, text="Endereço do Restaurante:", bg="black", fg="white").pack()
        self.restaurante_entry = tk.Entry(self.frame, width=50)
        self.restaurante_entry.insert(0, self.localizacao_atual)
        self.restaurante_entry.pack(pady=5)
        tk.Button(self.frame, text="Salvar Endereço", command=self.salvar_endereco,
                  fg="blue", activebackground="red", bg="lightgray").pack()
        tk.Label(self.frame, text="Taxa Diária (R$):", bg="black", fg="white").pack()
        self.daily_rate_entry = tk.Entry(self.frame, width=10)
        self.daily_rate_entry.insert(0, str(self.daily_rate))
        self.daily_rate_entry.pack()
        tk.Label(self.frame, text="Valor do Lanche (R$):", bg="black", fg="white").pack()
        self.lanche_entry = tk.Entry(self.frame, width=10)
        self.lanche_entry.insert(0, str(self.lanche_value))
        self.lanche_entry.pack()
        tk.Label(self.frame, text="Taxa de Entrega Base (R$) (até 4km):", bg="black", fg="white").pack()
        self.base_delivery_entry = tk.Entry(self.frame, width=10)
        self.base_delivery_entry.insert(0, str(self.base_delivery_fee))
        self.base_delivery_entry.pack()
        tk.Label(self.frame, text="Distância Limite (km):", bg="black", fg="white").pack()
        self.distance_threshold_entry = tk.Entry(self.frame, width=10)
        self.distance_threshold_entry.insert(0, str(self.distance_threshold))
        self.distance_threshold_entry.pack()
        tk.Label(self.frame, text="Taxa Extra por km (R$) acima de 4km:", bg="black", fg="white").pack()
        self.extra_rate_entry = tk.Entry(self.frame, width=10)
        self.extra_rate_entry.insert(0, str(self.extra_rate))
        self.extra_rate_entry.pack()
        tk.Button(self.frame, text="Confirmar Configuração", command=self.confirmar_configuracao,
                  fg="blue", activebackground="red", bg="lightgray").pack(pady=10)

    def salvar_endereco(self):
        endereco = self.restaurante_entry.get().strip()
        if not endereco:
            messagebox.showerror("Erro", "Informe o endereço do restaurante.")
            return
        self.localizacao_atual = endereco
        config = self.db.load_config()
        if config:
            self.db.save_config(endereco, config[1], config[2], config[3], config[4], config[5])
        else:
            self.db.save_config(endereco, self.daily_rate, self.lanche_value, self.base_delivery_fee, self.distance_threshold, self.extra_rate)
        messagebox.showinfo("Sucesso", "Endereço salvo com sucesso!")

    def confirmar_configuracao(self):
        self.localizacao_atual = self.restaurante_entry.get().strip()
        if not self.localizacao_atual:
            messagebox.showerror("Erro", "Informe o endereço do restaurante.")
            return
        try:
            self.daily_rate = float(self.daily_rate_entry.get().strip())
            self.lanche_value = float(self.lanche_entry.get().strip())
            self.base_delivery_fee = float(self.base_delivery_entry.get().strip())
            self.distance_threshold = float(self.distance_threshold_entry.get().strip())
            self.extra_rate = float(self.extra_rate_entry.get().strip())
        except:
            messagebox.showerror("Erro", "Valores de configuração inválidos.")
            return
        self.db.save_config(self.localizacao_atual, self.daily_rate, self.lanche_value, self.base_delivery_fee,
                            self.distance_threshold, self.extra_rate)
        self.master.after(0, self.criar_tela_entregas_execucao)

    def criar_tela_entregas_execucao(self):
        for widget in self.frame.winfo_children():
            widget.destroy()
        nome = self.motoboys_data[self.current_motoboy]["name"]
        tk.Label(self.frame, text=f"Motoboy: {nome}", font=("Arial", 12, "bold"), bg="black", fg="white").pack(pady=5)
        tk.Label(self.frame, text="Quantas entregas foram realizadas?", bg="black", fg="white").pack()
        self.entregas_entry = tk.Entry(self.frame, width=10)
        self.entregas_entry.pack()
        tk.Button(self.frame, text="Próximo", command=self.confirmar_num_entregas_execucao,
                  fg="blue", activebackground="red", bg="lightgray").pack(pady=5)

    def confirmar_num_entregas_execucao(self):
        try:
            num_entregas = int(self.entregas_entry.get().strip())
            if num_entregas < 0:
                raise ValueError
        except:
            messagebox.showerror("Erro", "Número inválido de entregas.")
            return
        self.motoboys_data[self.current_motoboy]["num_entregas"] = num_entregas
        self.motoboys_data[self.current_motoboy]["enderecos"] = []
        self.motoboys_data[self.current_motoboy]["entrega_info"] = []
        self.motoboys_data[self.current_motoboy]["resultado"] = None
        self.current_entrega = 0
        if num_entregas > 0:
            self.criar_tela_endereco_execucao()
        else:
            self.master.after(0, self.calcular_pagamento_motoboy)

    def criar_tela_endereco_execucao(self):
        for widget in self.frame.winfo_children():
            widget.destroy()
        nome = self.motoboys_data[self.current_motoboy]["name"]
        tk.Label(self.frame, text=f"Motoboy: {nome}", font=("Arial", 12, "bold"), bg="black", fg="white").pack(pady=5)
        tk.Label(self.frame, text=f"Informe o endereço da entrega {self.current_entrega+1}:", bg="black", fg="white").pack()
        self.endereco_entry = tk.Entry(self.frame, width=50)
        self.endereco_entry.pack()
        tk.Label(self.frame, text="Código da Comanda:", bg="black", fg="white").pack()
        self.comanda_entry = tk.Entry(self.frame, width=20)
        self.comanda_entry.pack()
        tk.Button(self.frame, text="Confirmar", command=self.confirmar_endereco_execucao,
                  fg="blue", activebackground="red", bg="lightgray").pack(pady=5)

    def confirmar_endereco_execucao(self):
        endereco = self.endereco_entry.get().strip()
        comanda = self.comanda_entry.get().strip()
        if not endereco:
            messagebox.showerror("Erro", "O endereço não pode ser vazio.")
            return
        if not comanda:
            resposta = messagebox.askyesno("Aviso", "Código da comanda não informado. Deseja prosseguir com código 000?\n(Se não informar, não será possível identificar o pedido.)")
            if resposta:
                comanda = "000"
            else:
                messagebox.showinfo("Atenção", "Por favor, informe o código da comanda.")
                return
        self.motoboys_data[self.current_motoboy]["enderecos"].append({"endereco": endereco, "comanda": comanda})
        self.current_entrega += 1
        if self.current_entregas_incompletas_execucao():
            self.criar_tela_endereco_execucao()
        else:
            self.master.after(0, self.calcular_pagamento_motoboy)

    def current_entregas_incompletas_execucao(self):
        return self.current_entrega < self.motoboys_data[self.current_motoboy]["num_entregas"]

    def calcular_valor_entrega(self, distance):
        """
        Calcula o valor da entrega com base na distância.
        Se a distância for menor ou igual ao limite, utiliza a taxa base.
        Caso contrário, adiciona uma taxa extra para cada km acima do limite.
        """
        if distance <= self.distance_threshold:
            return self.base_delivery_fee
        else:
            extra_km = distance - self.distance_threshold
            return self.base_delivery_fee + (extra_km * self.extra_rate)

    # --- NOVA LÓGICA: Cálculo da rota e distância via Mapbox usando a nova função ---
    def calcular_pagamento_motoboy(self):
        total_entrega = 0.0
        entrega_info = []
        enderecos = self.motoboys_data[self.current_motoboy]["enderecos"]
        # Exibe a tela de carregamento
        self.show_calculating_dialog()
        # Atualiza a barra de progresso: 1 passo por entrega
        self.progress_bar["maximum"] = len(enderecos)
        progress = 0
        for idx, item in enumerate(enderecos, start=1):
            self.update_loading_message(f"Calculando rota da entrega {idx}...")
            distance, tempo = calculate_distance_and_time(self.localizacao_atual, item["endereco"])
            progress += 1
            self.progress_bar["value"] = progress
            self.calculating_window.update_idletasks()
            if distance is None or tempo is None:
                distance, tempo = 0.0, 0
            valor = self.calcular_valor_entrega(distance)
            total_entrega += valor
            entrega_info.append({
                "endereco": item["endereco"],
                "comanda": item["comanda"],
                "distancia": distance,
                "tempo": tempo,
                "valor": valor
            })
        self.hide_calculating_dialog()
        total_final = self.daily_rate + self.lanche_value + total_entrega
        self.motoboys_data[self.current_motoboy]["entrega_info"] = entrega_info
        self.motoboys_data[self.current_motoboy]["resultado"] = total_final
        detalhes = "\n".join([f"{i+1}. {d['endereco']} (Código: {d['comanda']}) - {d['distancia']:.2f} km, {d['tempo']} min, R$ {d['valor']:.2f}" 
                              for i, d in enumerate(entrega_info)])
        motoboy_name = self.motoboys_data[self.current_motoboy]["name"]
        num_entregas = self.motoboys_data[self.current_motoboy]["num_entregas"]
        self.db.save_result(motoboy_name, total_final, num_entregas, total_entrega, detalhes)
        self.master.after(0, self.pos_calculo)

    def update_loading_message(self, message):
        if hasattr(self, 'loading_message_label'):
            self.loading_message_label.config(text=message)
            self.calculating_window.update_idletasks()

    def show_calculating_dialog(self):
        self.calc_start_time = time.time()
        self.calculating_window = tk.Toplevel(self.master)
        self.calculating_window.configure(bg="black")
        self.calculating_window.title("Calculando Rotas")
        tk.Label(self.calculating_window, text="Calculando rotas, aguarde...", bg="black", fg="white").pack(pady=10)
        self.loading_message_label = tk.Label(self.calculating_window, text="", bg="black", fg="white")
        self.loading_message_label.pack(pady=5)
        self.timer_label = tk.Label(self.calculating_window, text="Tempo: 0 s", bg="black", fg="white")
        self.timer_label.pack(pady=5)
        self.progress_bar = ttk.Progressbar(self.calculating_window, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(pady=5)
        self.update_timer()

    def update_timer(self):
        elapsed = int(time.time() - self.calc_start_time)
        self.timer_label.config(text=f"Tempo: {elapsed} s")
        if self.calculating_window.winfo_exists():
            self.calculating_window.after(1000, self.update_timer)

    def hide_calculating_dialog(self):
        if hasattr(self, 'calculating_window') and self.calculating_window.winfo_exists():
            self.calculating_window.destroy()

    def pos_calculo(self):
        nome = self.motoboys_data[self.current_motoboy]["name"]
        messagebox.showinfo("Resultado", f"Motoboy {nome} ganhou R$ {self.motoboys_data[self.current_motoboy]['resultado']:.2f}")
        self.current_motoboy += 1
        if self.current_motoboy < len(self.motoboys_data):
            self.criar_tela_entregas_execucao()
        else:
            self.mostrar_resultados_finais()

    def mostrar_resultados_finais(self):
        for widget in self.frame.winfo_children():
            widget.destroy()
        tk.Label(self.frame, text="Resultados Finais Detalhados:", font=("Arial", 14, "bold"),
                 bg="black", fg="white").pack(pady=5)
        for data in self.motoboys_data:
            tk.Label(self.frame, text=f"Motoboy: {data['name']}", font=("Arial", 12, "bold"),
                     bg="black", fg="white").pack(pady=(10, 0))
            columns = ("Entrega", "Endereço", "Distância (km)", "Tempo (min)", "Valor (R$)")
            frame_tree = tk.Frame(self.frame, bg="black")
            frame_tree.pack(pady=5, fill=tk.BOTH, expand=True)
            scrollbar = tk.Scrollbar(frame_tree, orient="vertical")
            tree = ttk.Treeview(frame_tree, columns=columns, show="headings", height=10, yscrollcommand=scrollbar.set)
            scrollbar.config(command=tree.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=300, anchor="center")
            for i, info in enumerate(data.get("entrega_info", []), start=1):
                tree.insert("", "end", values=(
                    i,
                    f"{info['endereco']} (Código: {info['comanda']})",
                    f"{info['distancia']:.2f}",
                    f"{info['tempo'] if info['tempo'] != 0 else 'N/A'}",
                    f"{info['valor']:.2f}"
                ))
            tree.insert("", "end", values=(
                "TOTAL",
                "",
                "",
                "",
                f"{data['resultado']:.2f}"
            ))
        tk.Button(self.frame, text="Voltar ao Menu", command=self.criar_menu_principal,
                  fg="blue", activebackground="red", bg="lightgray").pack(pady=10)

    def exibir_ranking(self):
        ranking = self.db.get_ranking()
        if not ranking:
            messagebox.showinfo("Ranking", "Não há dados para exibir o ranking.")
            return
        win = tk.Toplevel(self.master)
        win.configure(bg="black")
        win.title("Ranking de Motoboys")
        tree_frame = tk.Frame(win, bg="black")
        tree_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(tree_frame, orient="vertical")
        columns = ("Posição", "Motoboy", "Entregas", "Total Ganho com Taxas (R$)", "Total Ganho (R$)")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=10, yscrollcommand=scrollbar.set)
        scrollbar.config(command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=200, anchor="center")
        for i, row in enumerate(ranking, start=1):
            motoboy, total_deliveries, total_taxas, total_final = row
            tree.insert("", "end", values=(i, motoboy, total_deliveries, f"{total_taxas:.2f}", f"{total_final:.2f}"))
        tk.Button(win, text="Fechar", command=win.destroy,
                  fg="blue", activebackground="red", bg="lightgray").pack(pady=5)

    def criar_menu_principal(self):
        self.criar_tela_inicial()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
