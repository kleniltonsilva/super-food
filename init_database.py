#!/usr/bin/env python3
"""
Script de Inicialização do Banco de Dados
Cria schema completo + super admin padrão
"""

import os
import sys

# Adiciona raiz ao path
sys.path.append(os.path.dirname(__file__))

from database.session import init_db, criar_super_admin_padrao, get_db_session
from database.models import Restaurante, ConfigRestaurante
import hashlib
from datetime import datetime, timedelta

def criar_restaurante_teste():
    """Cria restaurante de teste para desenvolvimento"""
    session = get_db_session()
    try:
        # Verifica se já existe
        existe = session.query(Restaurante).filter(Restaurante.email == 'teste@superfood.com').first()
        if existe:
            print("⚠️  Restaurante de teste já existe")
            return
        
        # Cria restaurante
        restaurante = Restaurante(
            nome='Restaurante Teste',
            nome_fantasia='Teste Burguer',
            email='teste@superfood.com',
            telefone='11999999999',
            endereco_completo='Rua Teste, 123, São Paulo, SP',
            latitude=-23.550520,
            longitude=-46.633308,
            plano='premium',
            valor_plano=599.0,
            limite_motoboys=999,
            ativo=True,
            status='ativo',
            data_vencimento=datetime.now() + timedelta(days=365)
        )
        
        restaurante.set_senha('123456')
        restaurante.gerar_codigo_acesso()
        
        session.add(restaurante)
        session.flush()
        
        # Cria config
        config = ConfigRestaurante(
            restaurante_id=restaurante.id,
            status_atual='fechado',
            modo_despacho='auto_economico',
            raio_entrega_km=15.0,
            tempo_medio_preparo=30,
            despacho_automatico=True
        )
        
        session.add(config)
        session.commit()
        
        print(f"✅ Restaurante teste criado!")
        print(f"   Email: teste@superfood.com")
        print(f"   Senha: 123456")
        print(f"   Código Acesso Motoboy: {restaurante.codigo_acesso}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Erro: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    print("="*80)
    print("🚀 INICIALIZANDO BANCO DE DADOS - SUPER FOOD v2.1")
    print("="*80)
    
    print("\n1️⃣ Criando schema completo...")
    init_db()
    print("✅ Schema criado!")
    
    print("\n2️⃣ Criando super admin padrão...")
    criar_super_admin_padrao()
    
    print("\n3️⃣ Criando restaurante de teste...")
    criar_restaurante_teste()
    
    print("\n" + "="*80)
    print("✅ BANCO DE DADOS PRONTO!")
    print("="*80)
    print("\n📝 CREDENCIAIS:")
    print("   Super Admin: superadmin / SuperFood2025!")
    print("   Restaurante Teste: teste@superfood.com / 123456")
    print("\n🚀 Execute: streamlit run streamlit_app/super_admin.py")
    print("="*80)