"""
database.py - Sistema de Banco de Dados Unificado Multi-Restaurante
Gerencia TODAS as tabelas do sistema Super Food de forma integrada
"""

import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import json

class DatabaseManager:
    """Gerenciador central do banco de dados - Todas as operações passam por aqui"""
    
    def __init__(self, db_path: str = "super_food.db"):
        self.db_path = db_path
        self.conn = None
        self.init_database()
    
    def get_connection(self):
        """Retorna conexão com o banco"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def close(self):
        """Fecha conexão"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def init_database(self):
        """Inicializa TODAS as tabelas do sistema de forma integrada"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # ==================== SUPER ADMIN ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS super_admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL UNIQUE,
                senha_hash TEXT NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ==================== RESTAURANTES ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS restaurantes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_fantasia TEXT NOT NULL,
                razao_social TEXT,
                cnpj TEXT,
                email TEXT NOT NULL UNIQUE,
                telefone TEXT NOT NULL,
                endereco_completo TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                plano TEXT NOT NULL,
                valor_plano REAL NOT NULL,
                limite_motoboys INTEGER NOT NULL,
                status TEXT DEFAULT 'ativo',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_vencimento TIMESTAMP,
                senha_hash TEXT NOT NULL,
                codigo_acesso TEXT NOT NULL UNIQUE
            )
        ''')
        
        # ==================== ASSINATURAS ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assinaturas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurante_id INTEGER NOT NULL,
                data_pagamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                valor_pago REAL NOT NULL,
                forma_pagamento TEXT,
                status TEXT DEFAULT 'ativo',
                data_vencimento TIMESTAMP NOT NULL,
                observacoes TEXT,
                FOREIGN KEY (restaurante_id) REFERENCES restaurantes (id) ON DELETE CASCADE
            )
        ''')
        
        # ==================== CONFIGURAÇÕES DO RESTAURANTE ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config_restaurante (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurante_id INTEGER NOT NULL UNIQUE,
                horario_abertura TEXT DEFAULT '10:00',
                horario_fechamento TEXT DEFAULT '22:00',
                dias_semana_abertos TEXT DEFAULT 'segunda,terca,quarta,quinta,sexta,sabado,domingo',
                status_atual TEXT DEFAULT 'fechado',
                ultimo_login TIMESTAMP,
                
                -- Configurações de Entrega/Pagamento Motoboys
                valor_km REAL DEFAULT 1.5,
                valor_lanche REAL DEFAULT 15.0,
                taxa_entrega_base REAL DEFAULT 5.0,
                distancia_base_km REAL DEFAULT 4.0,
                taxa_km_extra REAL DEFAULT 1.5,
                taxa_diaria REAL DEFAULT 35.0,
                
                -- Modo de Despacho
                modo_despacho TEXT DEFAULT 'auto_economico',
                
                -- Integrações
                ifood_token TEXT,
                ifood_ativo INTEGER DEFAULT 0,
                site_cliente_ativo INTEGER DEFAULT 1,
                
                FOREIGN KEY (restaurante_id) REFERENCES restaurantes (id) ON DELETE CASCADE
            )
        ''')
        
        # ==================== MOTOBOYS ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS motoboys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurante_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                usuario TEXT NOT NULL,
                senha_hash TEXT NOT NULL,
                telefone TEXT,
                codigo_acesso TEXT NOT NULL,
                status TEXT DEFAULT 'disponivel',
                aprovado INTEGER DEFAULT 0,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_aprovacao TIMESTAMP,
                total_entregas INTEGER DEFAULT 0,
                total_ganhos REAL DEFAULT 0.0,
                avaliacao_media REAL DEFAULT 0.0,
                UNIQUE(restaurante_id, usuario),
                FOREIGN KEY (restaurante_id) REFERENCES restaurantes (id) ON DELETE CASCADE
            )
        ''')
        
        # ==================== SOLICITAÇÕES DE CADASTRO MOTOBOY ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS motoboys_solicitacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurante_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                usuario TEXT NOT NULL,
                telefone TEXT,
                codigo_acesso TEXT NOT NULL,
                data_solicitacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pendente',
                motivo_recusa TEXT,
                FOREIGN KEY (restaurante_id) REFERENCES restaurantes (id) ON DELETE CASCADE
            )
        ''')
        
        # ==================== PEDIDOS ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurante_id INTEGER NOT NULL,
                comanda TEXT NOT NULL,
                tipo TEXT NOT NULL,
                origem TEXT DEFAULT 'manual',
                
                -- Dados do Cliente
                cliente_nome TEXT NOT NULL,
                cliente_telefone TEXT,
                endereco_entrega TEXT,
                numero_mesa TEXT,
                latitude_cliente REAL,
                longitude_cliente REAL,
                
                -- Dados do Pedido
                itens TEXT NOT NULL,
                valor_total REAL DEFAULT 0.0,
                observacoes TEXT,
                
                -- Status e Tempo
                status TEXT DEFAULT 'pendente',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tempo_estimado INTEGER DEFAULT 30,
                horario_previsto TIMESTAMP,
                horario_finalizado TIMESTAMP,
                prioridade INTEGER DEFAULT 0,
                
                -- Despacho
                modo_despacho TEXT,
                despachado INTEGER DEFAULT 0,
                
                UNIQUE(restaurante_id, comanda),
                FOREIGN KEY (restaurante_id) REFERENCES restaurantes (id) ON DELETE CASCADE
            )
        ''')
        
        # ==================== ENTREGAS/ROTAS ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entregas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL,
                motoboy_id INTEGER NOT NULL,
                restaurante_id INTEGER NOT NULL,
                
                -- Endereços
                endereco_origem TEXT NOT NULL,
                endereco_destino TEXT NOT NULL,
                lat_origem REAL,
                lon_origem REAL,
                lat_destino REAL,
                lon_destino REAL,
                
                -- Métricas
                distancia_km REAL NOT NULL,
                tempo_estimado_min INTEGER NOT NULL,
                valor_entrega REAL NOT NULL,
                ordem_rota INTEGER DEFAULT 1,
                
                -- Status
                status TEXT DEFAULT 'aguardando',
                horario_atribuicao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                horario_saida TIMESTAMP,
                horario_entrega TIMESTAMP,
                motivo_cancelamento TEXT,
                
                -- Avaliação
                avaliacao_cliente INTEGER,
                feedback_cliente TEXT,
                
                FOREIGN KEY (pedido_id) REFERENCES pedidos (id) ON DELETE CASCADE,
                FOREIGN KEY (motoboy_id) REFERENCES motoboys (id) ON DELETE CASCADE,
                FOREIGN KEY (restaurante_id) REFERENCES restaurantes (id) ON DELETE CASCADE
            )
        ''')
        
        # ==================== CACHE DE DISTÂNCIAS ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_distancias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurante_id INTEGER NOT NULL,
                endereco_origem TEXT NOT NULL,
                endereco_origem_hash TEXT NOT NULL,
                endereco_destino TEXT NOT NULL,
                endereco_destino_hash TEXT NOT NULL,
                distancia_km REAL NOT NULL,
                tempo_estimado_min INTEGER NOT NULL,
                data_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                valido INTEGER DEFAULT 1,
                UNIQUE(restaurante_id, endereco_origem_hash, endereco_destino_hash),
                FOREIGN KEY (restaurante_id) REFERENCES restaurantes (id) ON DELETE CASCADE
            )
        ''')
        
        # ==================== CAIXA ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS caixa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurante_id INTEGER NOT NULL,
                data_abertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_fechamento TIMESTAMP,
                usuario_abertura TEXT NOT NULL,
                usuario_fechamento TEXT,
                
                valor_abertura REAL NOT NULL,
                valor_fechamento REAL,
                valor_retiradas REAL DEFAULT 0.0,
                total_vendas REAL DEFAULT 0.0,
                total_dinheiro REAL DEFAULT 0.0,
                total_cartao REAL DEFAULT 0.0,
                total_pix REAL DEFAULT 0.0,
                
                status TEXT DEFAULT 'aberto',
                observacoes TEXT,
                
                FOREIGN KEY (restaurante_id) REFERENCES restaurantes (id) ON DELETE CASCADE
            )
        ''')
        
        # ==================== MOVIMENTAÇÕES DO CAIXA ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS caixa_movimentacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caixa_id INTEGER NOT NULL,
                restaurante_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                valor REAL NOT NULL,
                forma_pagamento TEXT,
                descricao TEXT,
                pedido_id INTEGER,
                usuario TEXT,
                data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (caixa_id) REFERENCES caixa (id) ON DELETE CASCADE,
                FOREIGN KEY (restaurante_id) REFERENCES restaurantes (id) ON DELETE CASCADE,
                FOREIGN KEY (pedido_id) REFERENCES pedidos (id) ON DELETE SET NULL
            )
        ''')
        
        # ==================== GPS MOTOBOYS (Tempo Real) ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gps_motoboys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                motoboy_id INTEGER NOT NULL,
                restaurante_id INTEGER NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                velocidade REAL DEFAULT 0.0,
                precisao REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (motoboy_id) REFERENCES motoboys (id) ON DELETE CASCADE,
                FOREIGN KEY (restaurante_id) REFERENCES restaurantes (id) ON DELETE CASCADE
            )
        ''')
        
        # ==================== RANKING MOTOBOYS ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ranking_motoboys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurante_id INTEGER NOT NULL,
                motoboy_id INTEGER NOT NULL,
                periodo TEXT NOT NULL,
                data_inicio DATE NOT NULL,
                data_fim DATE NOT NULL,
                
                total_entregas INTEGER DEFAULT 0,
                total_ganhos REAL DEFAULT 0.0,
                total_distancia_km REAL DEFAULT 0.0,
                tempo_medio_entrega_min REAL DEFAULT 0.0,
                avaliacao_media REAL DEFAULT 0.0,
                
                posicao_entregas INTEGER,
                posicao_ganhos INTEGER,
                posicao_velocidade INTEGER,
                
                data_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE(restaurante_id, motoboy_id, periodo, data_inicio),
                FOREIGN KEY (restaurante_id) REFERENCES restaurantes (id) ON DELETE CASCADE,
                FOREIGN KEY (motoboy_id) REFERENCES motoboys (id) ON DELETE CASCADE
            )
        ''')
        
        # ==================== CARDÁPIO ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cardapio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurante_id INTEGER NOT NULL,
                categoria TEXT NOT NULL,
                nome_item TEXT NOT NULL,
                descricao TEXT,
                preco REAL NOT NULL,
                imagem_url TEXT,
                disponivel INTEGER DEFAULT 1,
                ordem INTEGER DEFAULT 0,
                tempo_preparo INTEGER DEFAULT 20,
                FOREIGN KEY (restaurante_id) REFERENCES restaurantes (id) ON DELETE CASCADE
            )
        ''')
        
        # ==================== NOTIFICAÇÕES ====================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notificacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurante_id INTEGER,
                motoboy_id INTEGER,
                tipo TEXT NOT NULL,
                titulo TEXT NOT NULL,
                mensagem TEXT NOT NULL,
                lida INTEGER DEFAULT 0,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_leitura TIMESTAMP,
                dados_extra TEXT,
                FOREIGN KEY (restaurante_id) REFERENCES restaurantes (id) ON DELETE CASCADE,
                FOREIGN KEY (motoboy_id) REFERENCES motoboys (id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        
        # Criar super admin padrão se não existir
        cursor.execute("SELECT * FROM super_admin WHERE usuario = 'superadmin'")
        if not cursor.fetchone():
            senha_hash = hashlib.sha256("SuperFood2025!".encode()).hexdigest()
            cursor.execute(
                "INSERT INTO super_admin (usuario, senha_hash) VALUES (?, ?)",
                ("superadmin", senha_hash)
            )
            conn.commit()
    
    # ==================== MÉTODOS DE RESTAURANTE ====================
    
    def criar_restaurante(self, dados: Dict[str, Any]) -> tuple[bool, str, Optional[int]]:
        """
        Cria restaurante + configuração inicial + código de acesso
        Retorna: (sucesso, mensagem, restaurante_id)
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Verificar se email já existe
            cursor.execute("SELECT id FROM restaurantes WHERE email = ?", (dados['email'],))
            if cursor.fetchone():
                return False, "Este email já está cadastrado!", None
            
            # Gerar código de acesso único (6 dígitos)
            import random
            while True:
                codigo = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                cursor.execute("SELECT id FROM restaurantes WHERE codigo_acesso = ?", (codigo,))
                if not cursor.fetchone():
                    break
            
            # Calcular data de vencimento
            data_vencimento = datetime.now() + timedelta(days=30)
            
            # Gerar senha padrão
            telefone_numeros = ''.join(filter(str.isdigit, dados['telefone']))
            senha_padrao = telefone_numeros[:6] if len(telefone_numeros) >= 6 else "123456"
            senha_hash = hashlib.sha256(senha_padrao.encode()).hexdigest()
            
            # Inserir restaurante
            cursor.execute('''
                INSERT INTO restaurantes (
                    nome_fantasia, razao_social, cnpj, email, telefone,
                    endereco_completo, plano, valor_plano, limite_motoboys,
                    data_vencimento, senha_hash, codigo_acesso
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                dados['nome_fantasia'],
                dados.get('razao_social', ''),
                dados.get('cnpj', ''),
                dados['email'],
                dados['telefone'],
                dados['endereco_completo'],
                dados['plano'],
                dados['valor_plano'],
                dados['limite_motoboys'],
                data_vencimento,
                senha_hash,
                codigo
            ))
            
            restaurante_id = cursor.lastrowid
            
            # Criar configuração inicial
            cursor.execute('''
                INSERT INTO config_restaurante (restaurante_id)
                VALUES (?)
            ''', (restaurante_id,))
            
            # Criar assinatura inicial
            cursor.execute('''
                INSERT INTO assinaturas (
                    restaurante_id, valor_pago, forma_pagamento, 
                    status, data_vencimento, observacoes
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                restaurante_id,
                dados['valor_plano'],
                'Primeira Mensalidade',
                'ativo',
                data_vencimento,
                'Criação do restaurante'
            ))
            
            conn.commit()
            
            msg = f"Restaurante criado! Código de Acesso: {codigo} | Senha: {senha_padrao}"
            return True, msg, restaurante_id
            
        except Exception as e:
            return False, f"Erro ao criar restaurante: {str(e)}", None
    
    def buscar_restaurante_por_email(self, email: str) -> Optional[Dict]:
        """Busca restaurante por email (para login)"""
        cursor = self.get_connection().cursor()
        cursor.execute("SELECT * FROM restaurantes WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def verificar_login_restaurante(self, email: str, senha: str) -> Optional[Dict]:
        """Verifica login do restaurante"""
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        cursor = self.get_connection().cursor()
        cursor.execute(
            "SELECT * FROM restaurantes WHERE email = ? AND senha_hash = ?",
            (email, senha_hash)
        )
        row = cursor.fetchone()
        
        if row:
            # Atualizar último login
            cursor.execute(
                "UPDATE config_restaurante SET ultimo_login = ? WHERE restaurante_id = ?",
                (datetime.now(), row['id'])
            )
            self.get_connection().commit()
            return dict(row)
        return None
    
    # ==================== MÉTODOS DE CONFIGURAÇÃO ====================
    
    def buscar_config_restaurante(self, restaurante_id: int) -> Optional[Dict]:
        """Busca configurações do restaurante"""
        cursor = self.get_connection().cursor()
        cursor.execute("SELECT * FROM config_restaurante WHERE restaurante_id = ?", (restaurante_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def atualizar_config_restaurante(self, restaurante_id: int, dados: Dict) -> bool:
        """Atualiza configurações do restaurante"""
        try:
            cursor = self.get_connection().cursor()
            
            set_clause = ", ".join([f"{k} = ?" for k in dados.keys()])
            values = list(dados.values()) + [restaurante_id]
            
            cursor.execute(
                f"UPDATE config_restaurante SET {set_clause} WHERE restaurante_id = ?",
                values
            )
            
            self.get_connection().commit()
            return True
        except Exception as e:
            print(f"Erro ao atualizar config: {e}")
            return False
    
    def abrir_restaurante(self, restaurante_id: int) -> bool:
        """Abre o restaurante (só funciona se houver horário configurado ou login)"""
        return self.atualizar_config_restaurante(restaurante_id, {'status_atual': 'aberto'})
    
    def fechar_restaurante(self, restaurante_id: int) -> bool:
        """Fecha o restaurante"""
        return self.atualizar_config_restaurante(restaurante_id, {'status_atual': 'fechado'})
    
    # ==================== MÉTODOS DE MOTOBOY ====================
    
    def criar_solicitacao_motoboy(self, dados: Dict) -> tuple[bool, str]:
        """Cria solicitação de cadastro de motoboy (aguarda aprovação)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Verificar código de acesso
            cursor.execute(
                "SELECT id FROM restaurantes WHERE id = ? AND codigo_acesso = ?",
                (dados['restaurante_id'], dados['codigo_acesso'])
            )
            if not cursor.fetchone():
                return False, "Código de acesso inválido!"
            
            # Verificar se usuário já existe
            cursor.execute(
                "SELECT id FROM motoboys WHERE restaurante_id = ? AND usuario = ?",
                (dados['restaurante_id'], dados['usuario'])
            )
            if cursor.fetchone():
                return False, "Usuário já existe neste restaurante!"
            
            # Criar solicitação
            cursor.execute('''
                INSERT INTO motoboys_solicitacoes (
                    restaurante_id, nome, usuario, telefone, codigo_acesso
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                dados['restaurante_id'],
                dados['nome'],
                dados['usuario'],
                dados.get('telefone', ''),
                dados['codigo_acesso']
            ))
            
            conn.commit()
            return True, "Solicitação enviada! Aguarde aprovação do restaurante."
            
        except Exception as e:
            return False, f"Erro: {str(e)}"
    
    def aprovar_motoboy(self, solicitacao_id: int, senha_padrao: str = "123456") -> tuple[bool, str]:
        """Aprova solicitação e cria conta do motoboy"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Buscar solicitação
            cursor.execute("SELECT * FROM motoboys_solicitacoes WHERE id = ?", (solicitacao_id,))
            sol = cursor.fetchone()
            
            if not sol:
                return False, "Solicitação não encontrada!"
            
            if sol['status'] != 'pendente':
                return False, "Solicitação já foi processada!"
            
            # Verificar limite de motoboys
            cursor.execute("SELECT limite_motoboys FROM restaurantes WHERE id = ?", (sol['restaurante_id'],))
            limite = cursor.fetchone()['limite_motoboys']
            
            cursor.execute(
                "SELECT COUNT(*) as total FROM motoboys WHERE restaurante_id = ? AND aprovado = 1",
                (sol['restaurante_id'],)
            )
            total_atual = cursor.fetchone()['total']
            
            if total_atual >= limite:
                return False, f"Limite de {limite} motoboys atingido!"
            
            # Criar motoboy
            senha_hash = hashlib.sha256(senha_padrao.encode()).hexdigest()
            
            cursor.execute('''
                INSERT INTO motoboys (
                    restaurante_id, nome, usuario, senha_hash, telefone,
                    codigo_acesso, aprovado, data_aprovacao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sol['restaurante_id'],
                sol['nome'],
                sol['usuario'],
                senha_hash,
                sol['telefone'],
                sol['codigo_acesso'],
                1,
                datetime.now()
            ))
            
            # Atualizar solicitação
            cursor.execute(
                "UPDATE motoboys_solicitacoes SET status = 'aprovado' WHERE id = ?",
                (solicitacao_id,)
            )
            
            conn.commit()
            return True, f"Motoboy aprovado! Senha padrão: {senha_padrao}"
            
        except Exception as e:
            return False, f"Erro: {str(e)}"
    
    def recusar_motoboy(self, solicitacao_id: int, motivo: str = "") -> tuple[bool, str]:
        """Recusa solicitação de motoboy"""
        try:
            cursor = self.get_connection().cursor()
            cursor.execute(
                "UPDATE motoboys_solicitacoes SET status = 'recusado', motivo_recusa = ? WHERE id = ?",
                (motivo, solicitacao_id)
            )
            self.get_connection().commit()
            return True, "Solicitação recusada."
        except Exception as e:
            return False, f"Erro: {str(e)}"
    
    def listar_solicitacoes_pendentes(self, restaurante_id: int) -> List[Dict]:
        """Lista solicitações pendentes de cadastro"""
        cursor = self.get_connection().cursor()
        cursor.execute(
            "SELECT * FROM motoboys_solicitacoes WHERE restaurante_id = ? AND status = 'pendente' ORDER BY data_solicitacao DESC",
            (restaurante_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def listar_motoboys(self, restaurante_id: int) -> List[Dict]:
        """Lista motoboys aprovados"""
        cursor = self.get_connection().cursor()
        cursor.execute(
            "SELECT * FROM motoboys WHERE restaurante_id = ? AND aprovado = 1 ORDER BY nome",
            (restaurante_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def excluir_motoboy(self, motoboy_id: int) -> tuple[bool, str]:
        """Exclui motoboy (deleta perfil e acesso)"""
        try:
            cursor = self.get_connection().cursor()
            cursor.execute("DELETE FROM motoboys WHERE id = ?", (motoboy_id,))
            self.get_connection().commit()
            return True, "Motoboy excluído com sucesso!"
        except Exception as e:
            return False, f"Erro: {str(e)}"
    
    # ==================== MÉTODOS DE PEDIDO ====================
    
    def criar_pedido(self, dados: Dict) -> tuple[bool, str, Optional[int]]:
        """Cria novo pedido"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Calcular horário previsto
            horario_previsto = datetime.now() + timedelta(minutes=dados.get('tempo_estimado', 30))
            
            cursor.execute('''
                INSERT INTO pedidos (
                    restaurante_id, comanda, tipo, origem,
                    cliente_nome, cliente_telefone, endereco_entrega, numero_mesa,
                    itens, valor_total, observacoes,
                    tempo_estimado, horario_previsto, modo_despacho
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                dados['restaurante_id'],
                dados['comanda'],
                dados['tipo'],
                dados.get('origem', 'manual'),
                dados['cliente_nome'],
                dados.get('cliente_telefone', ''),
                dados.get('endereco_entrega', ''),
                dados.get('numero_mesa', ''),
                dados['itens'],
                dados.get('valor_total', 0.0),
                dados.get('observacoes', ''),
                dados.get('tempo_estimado', 30),
                horario_previsto,
                dados.get('modo_despacho', 'auto_economico')
            ))
            
            pedido_id = cursor.lastrowid
            conn.commit()
            
            return True, "Pedido criado com sucesso!", pedido_id
            
        except Exception as e:
            return False, f"Erro: {str(e)}", None
    
    def listar_pedidos(self, restaurante_id: int, status: Optional[str] = None) -> List[Dict]:
        """Lista pedidos do restaurante"""
        cursor = self.get_connection().cursor()
        
        if status:
            cursor.execute(
                "SELECT * FROM pedidos WHERE restaurante_id = ? AND status = ? ORDER BY data_criacao DESC",
                (restaurante_id, status)
            )
        else:
            cursor.execute(
                "SELECT * FROM pedidos WHERE restaurante_id = ? ORDER BY data_criacao DESC",
                (restaurante_id,)
            )
        
        return [dict(row) for row in cursor.fetchall()]
    
    def atualizar_status_pedido(self, pedido_id: int, novo_status: str) -> bool:
        """Atualiza status do pedido"""
        try:
            cursor = self.get_connection().cursor()
            
            dados = {'status': novo_status}
            if novo_status in ['finalizado', 'entregue']:
                dados['horario_finalizado'] = datetime.now()
            
            cursor.execute(
                f"UPDATE pedidos SET status = ?, horario_finalizado = ? WHERE id = ?",
                (novo_status, dados.get('horario_finalizado'), pedido_id)
            )
            
            self.get_connection().commit()
            return True
        except:
            return False
    
    # ==================== MÉTODOS DE CAIXA ====================
    
    def abrir_caixa(self, restaurante_id: int, usuario: str, valor_abertura: float) -> tuple[bool, str, Optional[int]]:
        """Abre caixa do restaurante"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Verificar se já existe caixa aberto
            cursor.execute(
                "SELECT id FROM caixa WHERE restaurante_id = ? AND status = 'aberto'",
                (restaurante_id,)
            )
            if cursor.fetchone():
                return False, "Já existe um caixa aberto!", None
            
            # Abrir caixa
            cursor.execute('''
                INSERT INTO caixa (
                    restaurante_id, usuario_abertura, valor_abertura
                ) VALUES (?, ?, ?)
            ''', (restaurante_id, usuario, valor_abertura))
            
            caixa_id = cursor.lastrowid
            
            # Registrar movimentação
            cursor.execute('''
                INSERT INTO caixa_movimentacoes (
                    caixa_id, restaurante_id, tipo, valor, descricao, usuario
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (caixa_id, restaurante_id, 'abertura', valor_abertura, 'Abertura de caixa', usuario))
            
            conn.commit()
            return True, "Caixa aberto com sucesso!", caixa_id
            
        except Exception as e:
            return False, f"Erro: {str(e)}", None
    
    def registrar_venda_caixa(self, restaurante_id: int, pedido_id: int, valor: float, forma_pagamento: str) -> bool:
        """Registra venda no caixa"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Buscar caixa aberto
            cursor.execute(
                "SELECT id FROM caixa WHERE restaurante_id = ? AND status = 'aberto'",
                (restaurante_id,)
            )
            caixa = cursor.fetchone()
            
            if not caixa:
                return False
            
            caixa_id = caixa['id']
            
            # Atualizar totais
            cursor.execute(f'''
                UPDATE caixa SET 
                    total_vendas = total_vendas + ?,
                    total_{forma_pagamento.lower()} = total_{forma_pagamento.lower()} + ?
                WHERE id = ?
            ''', (valor, valor, caixa_id))
            
            # Registrar movimentação
            cursor.execute('''
                INSERT INTO caixa_movimentacoes (
                    caixa_id, restaurante_id, tipo, valor, forma_pagamento,
                    descricao, pedido_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (caixa_id, restaurante_id, 'venda', valor, forma_pagamento, f'Venda pedido #{pedido_id}', pedido_id))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Erro ao registrar venda: {e}")
            return False
    
    def registrar_retirada_caixa(self, restaurante_id: int, valor: float, descricao: str, usuario: str) -> bool:
        """Registra retirada de dinheiro do caixa"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id FROM caixa WHERE restaurante_id = ? AND status = 'aberto'",
                (restaurante_id,)
            )
            caixa = cursor.fetchone()
            
            if not caixa:
                return False
            
            caixa_id = caixa['id']
            
            # Atualizar retiradas
            cursor.execute(
                "UPDATE caixa SET valor_retiradas = valor_retiradas + ? WHERE id = ?",
                (valor, caixa_id)
            )
            
            # Registrar movimentação
            cursor.execute('''
                INSERT INTO caixa_movimentacoes (
                    caixa_id, restaurante_id, tipo, valor, descricao, usuario
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (caixa_id, restaurante_id, 'retirada', valor, descricao, usuario))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Erro ao registrar retirada: {e}")
            return False
    
    def fechar_caixa(self, restaurante_id: int, usuario: str, valor_fechamento: float) -> tuple[bool, str]:
        """Fecha caixa (só funciona se restaurante estiver fechado)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Verificar se restaurante está fechado
            cursor.execute(
                "SELECT status_atual FROM config_restaurante WHERE restaurante_id = ?",
                (restaurante_id,)
            )
            config = cursor.fetchone()
            
            if config and config['status_atual'] != 'fechado':
                return False, "Só pode fechar o caixa quando o restaurante estiver fechado!"
            
            # Buscar caixa aberto
            cursor.execute(
                "SELECT * FROM caixa WHERE restaurante_id = ? AND status = 'aberto'",
                (restaurante_id,)
            )
            caixa = cursor.fetchone()
            
            if not caixa:
                return False, "Nenhum caixa aberto!"
            
            # Fechar caixa
            cursor.execute('''
                UPDATE caixa SET 
                    status = 'fechado',
                    data_fechamento = ?,
                    usuario_fechamento = ?,
                    valor_fechamento = ?
                WHERE id = ?
            ''', (datetime.now(), usuario, valor_fechamento, caixa['id']))
            
            # Registrar movimentação
            cursor.execute('''
                INSERT INTO caixa_movimentacoes (
                    caixa_id, restaurante_id, tipo, valor, descricao, usuario
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (caixa['id'], restaurante_id, 'fechamento', valor_fechamento, 'Fechamento de caixa', usuario))
            
            conn.commit()
            
            # Calcular diferença
            esperado = caixa['valor_abertura'] + caixa['total_vendas'] - caixa['valor_retiradas']
            diferenca = valor_fechamento - esperado
            
            msg = f"Caixa fechado! Esperado: R$ {esperado:.2f} | Informado: R$ {valor_fechamento:.2f} | Diferença: R$ {diferenca:.2f}"
            return True, msg
            
        except Exception as e:
            return False, f"Erro: {str(e)}"
    
    def buscar_caixa_aberto(self, restaurante_id: int) -> Optional[Dict]:
        """Busca caixa aberto do restaurante"""
        cursor = self.get_connection().cursor()
        cursor.execute(
            "SELECT * FROM caixa WHERE restaurante_id = ? AND status = 'aberto'",
            (restaurante_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def listar_movimentacoes_caixa(self, caixa_id: int) -> List[Dict]:
        """Lista movimentações de um caixa"""
        cursor = self.get_connection().cursor()
        cursor.execute(
            "SELECT * FROM caixa_movimentacoes WHERE caixa_id = ? ORDER BY data_hora",
            (caixa_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== MÉTODOS DE CACHE DE DISTÂNCIAS ====================
    
    def buscar_distancia_cache(self, restaurante_id: int, origem: str, destino: str) -> Optional[Dict]:
        """Busca distância no cache"""
        origem_hash = hashlib.md5(origem.lower().strip().encode()).hexdigest()
        destino_hash = hashlib.md5(destino.lower().strip().encode()).hexdigest()
        
        cursor = self.get_connection().cursor()
        cursor.execute('''
            SELECT * FROM cache_distancias 
            WHERE restaurante_id = ? 
            AND endereco_origem_hash = ? 
            AND endereco_destino_hash = ?
            AND valido = 1
        ''', (restaurante_id, origem_hash, destino_hash))
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def salvar_distancia_cache(self, restaurante_id: int, origem: str, destino: str, distancia_km: float, tempo_min: int) -> bool:
        """Salva distância no cache"""
        try:
            origem_hash = hashlib.md5(origem.lower().strip().encode()).hexdigest()
            destino_hash = hashlib.md5(destino.lower().strip().encode()).hexdigest()
            
            cursor = self.get_connection().cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO cache_distancias (
                    restaurante_id, endereco_origem, endereco_origem_hash,
                    endereco_destino, endereco_destino_hash,
                    distancia_km, tempo_estimado_min
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (restaurante_id, origem, origem_hash, destino, destino_hash, distancia_km, tempo_min))
            
            self.get_connection().commit()
            return True
        except:
            return False
    
    def invalidar_cache_restaurante(self, restaurante_id: int) -> bool:
        """Invalida todo cache quando endereço do restaurante muda"""
        try:
            cursor = self.get_connection().cursor()
            cursor.execute(
                "UPDATE cache_distancias SET valido = 0 WHERE restaurante_id = ?",
                (restaurante_id,)
            )
            self.get_connection().commit()
            return True
        except:
            return False
    
    # ==================== MÉTODOS DE GPS MOTOBOY ====================
    
    def atualizar_gps_motoboy(self, motoboy_id: int, restaurante_id: int, lat: float, lon: float, velocidade: float = 0.0) -> bool:
        """Atualiza posição GPS do motoboy"""
        try:
            cursor = self.get_connection().cursor()
            
            cursor.execute('''
                INSERT INTO gps_motoboys (
                    motoboy_id, restaurante_id, latitude, longitude, velocidade
                ) VALUES (?, ?, ?, ?, ?)
            ''', (motoboy_id, restaurante_id, lat, lon, velocidade))
            
            self.get_connection().commit()
            return True
        except:
            return False
    
    def buscar_ultima_posicao_motoboy(self, motoboy_id: int) -> Optional[Dict]:
        """Busca última posição GPS do motoboy"""
        cursor = self.get_connection().cursor()
        cursor.execute(
            "SELECT * FROM gps_motoboys WHERE motoboy_id = ? ORDER BY timestamp DESC LIMIT 1",
            (motoboy_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # ==================== MÉTODOS DE RANKING ====================
    
    def atualizar_ranking_motoboy(self, motoboy_id: int, restaurante_id: int) -> bool:
        """Atualiza ranking do motoboy (chamado após cada entrega)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Buscar estatísticas do motoboy
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_entregas,
                    SUM(valor_entrega) as total_ganhos,
                    SUM(distancia_km) as total_distancia,
                    AVG(
                        (strftime('%s', horario_entrega) - strftime('%s', horario_saida)) / 60.0
                    ) as tempo_medio
                FROM entregas
                WHERE motoboy_id = ? AND status = 'entregue'
            ''', (motoboy_id,))
            
            stats = cursor.fetchone()
            
            if stats and stats['total_entregas'] > 0:
                # Atualizar totais do motoboy
                cursor.execute('''
                    UPDATE motoboys SET
                        total_entregas = ?,
                        total_ganhos = ?
                    WHERE id = ?
                ''', (stats['total_entregas'], stats['total_ganhos'] or 0, motoboy_id))
                
                conn.commit()
                return True
            
            return False
            
        except Exception as e:
            print(f"Erro ao atualizar ranking: {e}")
            return False
    
    def buscar_ranking_restaurante(self, restaurante_id: int, ordem: str = 'entregas') -> List[Dict]:
        """
        Busca ranking dos motoboys do restaurante
        ordem: 'entregas', 'ganhos', 'velocidade'
        """
        cursor = self.get_connection().cursor()
        
        ordem_sql = {
            'entregas': 'total_entregas DESC',
            'ganhos': 'total_ganhos DESC',
            'velocidade': 'total_entregas DESC, avaliacao_media DESC'  # Quem fez mais entregas mais rápido
        }
        
        cursor.execute(f'''
            SELECT 
                m.*,
                COALESCE(
                    (SELECT AVG((strftime('%s', horario_entrega) - strftime('%s', horario_saida)) / 60.0)
                     FROM entregas 
                     WHERE motoboy_id = m.id AND status = 'entregue'),
                    0
                ) as tempo_medio_entrega
            FROM motoboys m
            WHERE m.restaurante_id = ? AND m.aprovado = 1
            ORDER BY {ordem_sql.get(ordem, 'total_entregas DESC')}
        ''', (restaurante_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== MÉTODOS DE NOTIFICAÇÃO ====================
    
    def criar_notificacao(self, tipo: str, titulo: str, mensagem: str, 
                         restaurante_id: Optional[int] = None, 
                         motoboy_id: Optional[int] = None,
                         dados_extra: Optional[Dict] = None) -> bool:
        """Cria notificação para restaurante ou motoboy"""
        try:
            cursor = self.get_connection().cursor()
            
            cursor.execute('''
                INSERT INTO notificacoes (
                    restaurante_id, motoboy_id, tipo, titulo, mensagem, dados_extra
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                restaurante_id,
                motoboy_id,
                tipo,
                titulo,
                mensagem,
                json.dumps(dados_extra) if dados_extra else None
            ))
            
            self.get_connection().commit()
            return True
        except:
            return False
    
    def listar_notificacoes(self, restaurante_id: Optional[int] = None, 
                           motoboy_id: Optional[int] = None,
                           apenas_nao_lidas: bool = False) -> List[Dict]:
        """Lista notificações"""
        cursor = self.get_connection().cursor()
        
        query = "SELECT * FROM notificacoes WHERE "
        params = []
        
        if restaurante_id:
            query += "restaurante_id = ? "
            params.append(restaurante_id)
        elif motoboy_id:
            query += "motoboy_id = ? "
            params.append(motoboy_id)
        else:
            query += "1=1 "
        
        if apenas_nao_lidas:
            query += "AND lida = 0 "
        
        query += "ORDER BY data_criacao DESC LIMIT 50"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def marcar_notificacao_lida(self, notificacao_id: int) -> bool:
        """Marca notificação como lida"""
        try:
            cursor = self.get_connection().cursor()
            cursor.execute(
                "UPDATE notificacoes SET lida = 1, data_leitura = ? WHERE id = ?",
                (datetime.now(), notificacao_id)
            )
            self.get_connection().commit()
            return True
        except:
            return False


# ==================== FUNÇÕES AUXILIARES ====================

def gerar_senha_aleatoria(tamanho: int = 6) -> str:
    """Gera senha aleatória numérica"""
    import random
    return ''.join([str(random.randint(0, 9)) for _ in range(tamanho)])

def formatar_telefone(telefone: str) -> str:
    """Formata telefone removendo caracteres especiais"""
    return ''.join(filter(str.isdigit, telefone))

def validar_email(email: str) -> bool:
    """Valida formato de email"""
    import re
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None


# ==================== INSTÂNCIA GLOBAL ====================
# Usar esta instância em todo o sistema para garantir consistência

_db_instance = None

def get_db() -> DatabaseManager:
    """Retorna instância única do banco de dados (Singleton)"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance