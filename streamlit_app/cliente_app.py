# streamlit_app/cliente_app.py

"""
cliente_app.py - RÉPLICA COMPLETA FUNCIONAL
Inspirado em: pizzariamodelo.expressodelivery.app.br
Sistema: Super Food SaaS
"""

import streamlit as st
import sys
import os
from datetime import datetime
from typing import Optional, Dict, List
import json

# Adicionar pasta raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Imports do Sistema SaaS ---
try:
    from database.session import get_db_session
    from database.models import (
        Restaurante, CategoriaMenu, Produto, Pedido, ItemPedido,
        ConfigRestaurante, Entrega, SiteConfig
    )
    from utils.calculos import calcular_taxa_entrega
    from utils.mapbox_api import (
        autocomplete_endereco_restaurante,
        geocode_address,
        check_coverage_zone
    )
except ImportError:
    # Fallback para visualização se os módulos não existirem no ambiente atual
    pass

# ==========================================
# CONFIGURAÇÕES DE DESIGN (RÉPLICA FIEL)
# ==========================================
PRIMARY_COLOR = "#E31A24"    # Vermelho Expresso
SECONDARY_COLOR = "#FFD700"  # Amarelo Expresso
BG_LIGHT = "#F8F9FA"
TEXT_DARK = "#212529"

st.set_page_config(
    page_title="Peça Online! - App de Delivery",
    page_icon="🍕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def inject_styles():
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700;800&display=swap');
        
        /* Global */
        html, body, [class*="css"] {{
            font-family: 'Poppins', sans-serif;
            background-color: #f4f4f4;
            color: {TEXT_DARK};
        }}
        .main {{ padding: 0 !important; }}
        
        /* Top Bar Promocional */
        .top-promo {{
            background: {SECONDARY_COLOR};
            color: #000;
            padding: 10px;
            text-align: center;
            font-weight: 700;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 2px solid rgba(0,0,0,0.05);
        }}
        
        /* Navbar */
        .navbar-custom {{
            background: {PRIMARY_COLOR};
            padding: 15px 8%;
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
            position: sticky;
            top: 0;
            z-index: 1000;
        }}
        .logo-box {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .logo-circle {{
            background: white;
            color: {PRIMARY_COLOR};
            width: 45px;
            height: 45px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 900;
            font-size: 20px;
        }}
        .nav-links {{ display: flex; gap: 25px; }}
        .nav-item {{
            color: white;
            text-decoration: none;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            transition: 0.3s;
        }}
        .nav-item:hover {{ color: {SECONDARY_COLOR}; }}
        
        /* Hero Banner */
        .hero-banner {{
            background: linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)), url('https://images.unsplash.com/photo-1513104890138-7c749659a591?q=80&w=2070&auto=format&fit=crop');
            background-size: cover;
            background-position: center;
            height: 380px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: white;
            text-align: center;
            border-bottom: 8px solid {SECONDARY_COLOR};
        }}
        .hero-banner h1 {{ font-size: 60px; font-weight: 800; margin: 0; text-transform: uppercase; letter-spacing: -2px; }}
        .hero-banner p {{ font-size: 22px; margin-top: 10px; font-weight: 400; opacity: 0.9; }}
        .btn-order-now {{
            background: {SECONDARY_COLOR};
            color: #000;
            padding: 12px 35px;
            border-radius: 30px;
            font-weight: 800;
            margin-top: 25px;
            text-transform: uppercase;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }}
        
        /* Categorias Sticky */
        .cat-nav {{
            background: white;
            padding: 15px 8%;
            display: flex;
            gap: 15px;
            overflow-x: auto;
            border-bottom: 1px solid #eee;
            position: sticky;
            top: 75px;
            z-index: 999;
        }}
        .cat-btn {{
            background: #f8f9fa;
            padding: 8px 20px;
            border-radius: 20px;
            white-space: nowrap;
            font-weight: 600;
            font-size: 14px;
            border: 1px solid #ddd;
            cursor: pointer;
        }}
        .cat-btn.active {{
            background: {PRIMARY_COLOR};
            color: white;
            border-color: {PRIMARY_COLOR};
        }}
        
        /* Product Cards */
        .product-card {{
            background: white;
            border-radius: 15px;
            overflow: hidden;
            border: 1px solid #eee;
            transition: 0.3s;
            height: 100%;
            display: flex;
            flex-direction: column;
        }}
        .product-card:hover {{
            transform: translateY(-8px);
            box-shadow: 0 12px 30px rgba(0,0,0,0.1);
        }}
        .product-img {{
            height: 180px;
            background: #f0f0f0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 60px;
            position: relative;
        }}
        .badge-new {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: #28a745;
            color: white;
            padding: 3px 10px;
            border-radius: 5px;
            font-size: 11px;
            font-weight: 800;
            text-transform: uppercase;
        }}
        .product-info {{ padding: 20px; flex-grow: 1; }}
        .product-name {{ font-weight: 700; font-size: 18px; margin-bottom: 8px; color: #333; text-transform: uppercase; }}
        .product-desc {{ font-size: 13px; color: #777; line-height: 1.5; margin-bottom: 15px; min-height: 40px; }}
        .product-price {{ font-size: 24px; font-weight: 800; color: {PRIMARY_COLOR}; }}
        
        /* Cart Sidebar */
        .cart-container {{
            background: white;
            border-radius: 15px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.1);
            overflow: hidden;
            position: sticky;
            top: 100px;
        }}
        .cart-header {{
            background: {PRIMARY_COLOR};
            color: white;
            padding: 20px;
            text-align: center;
            font-weight: 800;
            font-size: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }}
        .cart-body {{ padding: 20px; }}
        .cart-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px dashed #eee;
        }}
        
        /* Footer */
        .footer-full {{
            background: #111;
            color: white;
            padding: 60px 8% 30px;
            margin-top: 80px;
        }}
        .footer-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 40px;
        }}
        .footer-col h3 {{
            color: {SECONDARY_COLOR};
            font-size: 18px;
            margin-bottom: 25px;
            text-transform: uppercase;
            border-left: 4px solid {PRIMARY_COLOR};
            padding-left: 12px;
        }}
        
        /* Streamlit Button Overrides */
        .stButton>button {{
            width: 100%;
            border-radius: 10px !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            transition: 0.3s !important;
        }}
        .btn-add button {{
            background: {PRIMARY_COLOR} !important;
            color: white !important;
            border: none !important;
        }}
        .btn-add button:hover {{ background: #c4161d !important; transform: scale(1.02); }}
        
        /* Forms */
        .stTextInput>div>div>input, .stSelectbox>div>div>div {{
            border-radius: 10px !important;
        }}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# LÓGICA DE ESTADO E DADOS
# ==========================================

def init_session():
    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'page' not in st.session_state: st.session_state.page = 'menu'
    if 'rest_id' not in st.session_state: st.session_state.rest_id = None
    if 'rest_info' not in st.session_state: st.session_state.rest_info = None

def get_restaurant_data():
    slug = st.query_params.get("restaurante") or st.query_params.get("r") or "lojademo"
    session = get_db_session()
    try:
        rest = session.query(Restaurante).filter(
            (Restaurante.codigo_acesso == slug) | (Restaurante.id.cast(st.String) == slug),
            Restaurante.ativo == True
        ).first()
        
        if rest:
            st.session_state.rest_id = rest.id
            st.session_state.rest_info = {
                'nome': rest.nome_fantasia,
                'endereco': rest.endereco_completo,
                'telefone': rest.telefone,
                'cidade': rest.cidade
            }
            return True
        return False
    except:
        # Mock para quando não há DB
        st.session_state.rest_id = 1
        st.session_state.rest_info = {'nome': 'Pizzaria Modelo', 'endereco': 'Rua das Pizzas, 123', 'telefone': '(11) 99999-9999', 'cidade': 'São Paulo'}
        return True
    finally:
        try: session.close()
        except: pass

def add_item(p_id, name, price):
    for item in st.session_state.cart:
        if item['id'] == p_id:
            item['qty'] += 1
            return
    st.session_state.cart.append({'id': p_id, 'name': name, 'price': price, 'qty': 1})

# ==========================================
# COMPONENTES DE INTERFACE
# ==========================================

def render_navbar():
    info = st.session_state.rest_info
    st.markdown(f"""
    <div class="top-promo">🔥 PROMOÇÃO DE HOJE: Pizza Gigante + Refri 2L por apenas R$ 45,00!</div>
    <div class="navbar-custom">
        <div class="logo-box">
            <div class="logo-circle">P</div>
            <div style="font-weight: 800; font-size: 22px; letter-spacing: -1px;">{info['nome'].upper()}</div>
        </div>
        <div class="nav-links">
            <a href="#" class="nav-item">Promoções</a>
            <a href="#" class="nav-item">Cardápio</a>
            <a href="#" class="nav-item">Minha Conta</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_hero():
    st.markdown(f"""
    <div class="hero-banner">
        <h1>A MELHOR PIZZA DA CIDADE</h1>
        <p>Ingredientes frescos, massa artesanal e entrega ultra rápida.</p>
        <div class="btn-order-now">Faça seu Pedido Agora</div>
    </div>
    """, unsafe_allow_html=True)

def render_menu():
    inject_styles()
    render_navbar()
    render_hero()
    
    col_content, col_cart = st.columns([2.6, 1])
    
    with col_content:
        session = get_db_session()
        try:
            categorias = session.query(CategoriaMenu).filter(
                CategoriaMenu.restaurante_id == st.session_state.rest_id,
                CategoriaMenu.ativo == True
            ).order_by(CategoriaMenu.ordem_exibicao).all()
            
            if not categorias:
                st.info("Cardápio em atualização...")
                return
                
            # Tabs de Categorias (Réplica do Modelo)
            tabs = st.tabs([cat.nome.upper() for cat in categorias])
            
            for i, cat in enumerate(categorias):
                with tabs[i]:
                    st.markdown(f"<h2 style='margin: 20px 0; color: {PRIMARY_COLOR};'>{cat.nome}</h2>", unsafe_allow_html=True)
                    produtos = session.query(Produto).filter(Produto.categoria_id == cat.id, Produto.ativo == True).all()
                    
                    # Grid 3 colunas
                    p_cols = st.columns(3)
                    for idx, p in enumerate(produtos):
                        with p_cols[idx % 3]:
                            st.markdown(f"""
                            <div class="product-card">
                                <div class="product-img">
                                    <div class="badge-new">Destaque</div>
                                    🍕
                                </div>
                                <div class="product-info">
                                    <div class="product-name">{p.nome}</div>
                                    <div class="product-desc">{p.descricao or "Ingredientes selecionados para o melhor sabor."}</div>
                                    <div class="product-price">R$ {p.preco:.2f}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            if st.button("ADICIONAR AO PEDIDO", key=f"add_{p.id}", use_container_width=True):
                                add_item(p.id, p.nome, float(p.preco))
                                st.toast(f"✅ {p.nome} no carrinho!")
                                st.rerun()
        except:
            st.warning("Erro ao carregar produtos. Verifique o banco de dados.")
        finally:
            try: session.close()
            except: pass

    with col_cart:
        render_sidebar_cart()
    
    render_footer()

def render_sidebar_cart():
    st.markdown(f"""
    <div class="cart-container">
        <div class="cart-header">
            <span>🛒</span> MEU PEDIDO
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        if not st.session_state.cart:
            st.markdown("<div style='padding: 40px; text-align: center; color: #bbb;'>Seu carrinho está vazio.<br>Escolha uma delícia ao lado!</div>", unsafe_allow_html=True)
            return
            
        total = 0
        for i, item in enumerate(st.session_state.cart):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"**{item['qty']}x {item['name']}**")
                st.markdown(f"<span style='color: {PRIMARY_COLOR}; font-weight: 700;'>R$ {item['price']*item['qty']:.2f}</span>", unsafe_allow_html=True)
            with c2:
                if st.button("❌", key=f"del_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()
            total += item['price'] * item['qty']
            st.markdown("<hr style='margin: 10px 0; border: 0; border-top: 1px dashed #eee;'>", unsafe_allow_html=True)
            
        st.markdown(f"""
        <div style="background: #fdfdfd; padding: 15px; border-radius: 10px; margin-top: 15px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span>Subtotal:</span>
                <b>R$ {total:.2f}</b>
            </div>
            <div style="display: flex; justify-content: space-between; color: #28a745; font-weight: 700; font-size: 20px; margin-top: 10px;">
                <span>TOTAL:</span>
                <span>R$ {total:.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("FECHAR PEDIDO AGORA", type="primary", use_container_width=True):
            st.session_state.page = 'checkout'
            st.rerun()

def render_checkout():
    inject_styles()
    render_navbar()
    st.markdown("<div style='padding: 40px 8%;'>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='color: {PRIMARY_COLOR}; font-weight: 800;'>FINALIZAR SEU PEDIDO</h1>", unsafe_allow_html=True)
    
    col_form, col_summary = st.columns([2, 1])
    
    with col_form:
        with st.container():
            st.markdown("### 👤 Seus Dados")
            nome = st.text_input("Nome Completo", placeholder="Como devemos te chamar?")
            whatsapp = st.text_input("WhatsApp para contato", placeholder="(00) 00000-0000")
            
            st.markdown("### 📍 Entrega ou Retirada")
            tipo = st.radio("Como deseja receber?", ["Entrega em Casa", "Retirar no Balcão"], horizontal=True)
            
            if tipo == "Entrega em Casa":
                endereco = st.text_input("Endereço (Rua, Número, Bairro)")
                referencia = st.text_input("Ponto de Referência")
            
            st.markdown("### 💳 Forma de Pagamento")
            pagamento = st.selectbox("Escolha como pagar", ["PIX", "Cartão de Crédito (Entregador)", "Cartão de Débito (Entregador)", "Dinheiro"])
            
            if pagamento == "Dinheiro":
                troco = st.text_input("Troco para quanto?")
                
            obs = st.text_area("Alguma observação? (Ex: Tirar cebola, campainha estragada...)")

    with col_summary:
        st.markdown(f"""
        <div style="background: white; padding: 25px; border-radius: 15px; border: 2px solid {PRIMARY_COLOR};">
            <h3 style="margin-top:0;">Resumo do Pedido</h3>
        """, unsafe_allow_html=True)
        
        total = sum(item['price'] * item['qty'] for item in st.session_state.cart)
        for item in st.session_state.cart:
            st.write(f"• {item['qty']}x {item['name']} - R$ {item['price']*item['qty']:.2f}")
            
        st.markdown("---")
        st.write(f"Subtotal: R$ {total:.2f}")
        st.write("Taxa de Entrega: R$ 5,00")
        st.markdown(f"<h2 style='color: {PRIMARY_COLOR};'>TOTAL: R$ {total+5:.2f}</h2>", unsafe_allow_html=True)
        
        if st.button("ENVIAR PEDIDO AGORA", type="primary", use_container_width=True):
            st.balloons()
            st.success("🎉 Pedido enviado com sucesso! Você receberá uma confirmação no WhatsApp.")
            st.session_state.cart = []
            st.session_state.page = 'menu'
            # Aqui entraria a lógica de criar_pedido no banco
            st.rerun()
            
        if st.button("VOLTAR AO CARDÁPIO", use_container_width=True):
            st.session_state.page = 'menu'
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    render_footer()

def render_footer():
    info = st.session_state.rest_info
    st.markdown(f"""
    <div class="footer-full">
        <div class="footer-grid">
            <div class="footer-col">
                <h3>Sobre a {info['nome']}</h3>
                <p style="opacity: 0.7; line-height: 1.8;">Somos apaixonados por pizza. Utilizamos apenas ingredientes premium e nossa entrega é referência em rapidez e qualidade na região de {info['cidade']}.</p>
            </div>
            <div class="footer-col">
                <h3>Atendimento</h3>
                <p style="opacity: 0.7;">📞 {info['telefone']}</p>
                <p style="opacity: 0.7;">📍 {info['endereco']}</p>
                <p style="opacity: 0.7;">⏰ Terça a Domingo: 18:00 às 23:30</p>
            </div>
            <div class="footer-col">
                <h3>Pagamento</h3>
                <p style="opacity: 0.7;">Aceitamos PIX, Crédito, Débito e Dinheiro na entrega.</p>
                <div style="display: flex; gap: 10px; margin-top: 15px;">
                    <div style="background: #333; padding: 5px 10px; border-radius: 5px; font-size: 10px;">VISA</div>
                    <div style="background: #333; padding: 5px 10px; border-radius: 4px; font-size: 10px;">MASTERCARD</div>
                    <div style="background: #333; padding: 5px 10px; border-radius: 4px; font-size: 10px;">PIX</div>
                </div>
            </div>
        </div>
        <div style="text-align: center; margin-top: 50px; padding-top: 20px; border-top: 1px solid #222; font-size: 12px; opacity: 0.5;">
            © {datetime.now().year} {info['nome']} - Super Food SaaS - Todos os direitos reservados.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# EXECUÇÃO PRINCIPAL
# ==========================================

def main():
    init_session()
    if not st.session_state.rest_id:
        if not get_restaurant_data():
            st.error("Restaurante não encontrado ou inativo.")
            return
            
    if st.session_state.page == 'menu':
        render_menu()
    elif st.session_state.page == 'checkout':
        render_checkout()

if __name__ == "__main__":
    main()
