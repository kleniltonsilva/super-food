#!/usr/bin/env python3
"""
test_stress_50_conversas.py — Stress Test REAL: 50 conversas simultâneas grok-3-mini-fast

Teste às cegas: dois agentes LLM independentes, sem saber que o outro é IA:
  1. Agente "Dono" — grok-3-mini-fast simulando 50 perfis de donos de restaurantes
  2. Agente "Ana" — grok-3-mini-fast com o system prompt real do bot de vendas

Métricas coletadas:
  - Tempo de resposta (média/p50/p95/max)
  - Taxa de convencimento (trial/demo pedido)
  - Taxa de handoff / opt-out
  - Erros e timeouts
  - Custo estimado
  - Qualidade (nota 1-5 pelo agente Dono)

REQUER: XAI_API_KEY configurada.
Rodar:
  XAI_API_KEY=... python tests/test_stress_50_conversas.py
  XAI_API_KEY=... python -m pytest tests/test_stress_50_conversas.py -v -s --timeout=600
"""
import os
import sys
import json
import time
import asyncio
import random
import statistics
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

# Adicionar path do projeto
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import httpx
except ImportError:
    print("ERRO: httpx não instalado. pip install httpx")
    sys.exit(1)

# ============================================================
# CONFIGURAÇÃO
# ============================================================

XAI_API_URL = "https://api.x.ai/v1/chat/completions"
MODEL = "grok-3-mini-fast"
MAX_TURNOS = 12
MIN_TURNOS = 6
TIMEOUT_PER_CALL = 60  # segundos
MAX_RETRIES = 2
PRECO_INPUT_POR_M = 0.30   # $0.30 por milhão tokens input
PRECO_OUTPUT_POR_M = 0.50  # $0.50 por milhão tokens output

# Rate limits xAI API (por tier):
#   Free:   5 RPM,  15k TPM input
#   Tier 1: 60 RPM, 100k TPM input
#   Tier 2+: mais alto (escala com spend)
# O semaphore controla quantas chamadas concorrentes — NÃO é RPM.
# Com 60 RPM e ~2s por chamada, podemos ter ~120 chamadas/min com semaphore 60.
# Usamos SEMAPHORE_LIMIT=50 (seguro para Tier 1+; para Free tier, reduzir para 5).
SEMAPHORE_LIMIT = int(os.environ.get("STRESS_SEMAPHORE", "50"))


# ============================================================
# 50 PERFIS DE RESTAURANTES
# ============================================================

PERFIS = [
    # --- 1. DESCONFIADOS (5) ---
    {
        "id": 1, "nome": "Carlos", "restaurante": "Bar do Carlão", "cidade": "São Paulo/SP",
        "tipo": "Bar e petiscos", "categoria": "desconfiado",
        "personalidade": "Desconfiado, quer saber quem indicou. Fala pouco, respostas curtas.",
        "cenario": "Nunca ouviu falar da Derekh. Acha que é golpe. Não clica em links.",
        "abertura": "Quem é você? Como conseguiu meu número?"
    },
    {
        "id": 2, "nome": "Dona Fátima", "restaurante": "Cantina da Fátima", "cidade": "Belo Horizonte/MG",
        "tipo": "Comida caseira", "categoria": "desconfiado",
        "personalidade": "Senhora de 60 anos, desconfia de tecnologia. Tem medo de cair em golpe.",
        "cenario": "Acha que vão clonar o WhatsApp dela. Não confia em empresa online.",
        "abertura": "Não conheço essa empresa. Isso é golpe?"
    },
    {
        "id": 3, "nome": "Marcos", "restaurante": "Espetaria do Marcos", "cidade": "Curitiba/PR",
        "tipo": "Espetaria", "categoria": "desconfiado",
        "personalidade": "Jovem mas cético. Pesquisa tudo no Google antes de decidir.",
        "cenario": "Quer saber CNPJ, site, reclame aqui. Não acredita em promessas.",
        "abertura": "Vocês têm CNPJ? Posso ver no Reclame Aqui?"
    },
    {
        "id": 4, "nome": "Priscila", "restaurante": "Pris Sushi", "cidade": "Rio de Janeiro/RJ",
        "tipo": "Sushi delivery", "categoria": "desconfiado",
        "personalidade": "Já caiu em golpe antes. Muito resistente a qualquer abordagem.",
        "cenario": "Foi enganada por outro sistema que prometeu e não entregou.",
        "abertura": "Já tentei um sistema desses e me deu prejuízo. Não quero mais."
    },
    {
        "id": 5, "nome": "Seu Antônio", "restaurante": "Padaria São Jorge", "cidade": "Porto Alegre/RS",
        "tipo": "Padaria/confeitaria", "categoria": "desconfiado",
        "personalidade": "Idoso, fala devagar, desconfia de tudo que é digital.",
        "cenario": "Não sabe mexer em tecnologia. O filho é quem cuida do WhatsApp.",
        "abertura": "Meu filho que mexe nisso. Não entendo nada de internet."
    },

    # --- 2. JÁ TEM IFOOD (5) ---
    {
        "id": 6, "nome": "Rafaela", "restaurante": "Rafa Burgers", "cidade": "Campinas/SP",
        "tipo": "Hamburgueria", "categoria": "ja_tem_ifood",
        "personalidade": "Satisfeita com iFood. Vende bem lá. Não vê motivo para mudar.",
        "cenario": "Faz 200 pedidos/mês no iFood. Acha que já resolve.",
        "abertura": "Já uso iFood e tá funcionando bem. Não preciso de mais nada."
    },
    {
        "id": 7, "nome": "Thiago", "restaurante": "Pizzaria Bella", "cidade": "Florianópolis/SC",
        "tipo": "Pizzaria", "categoria": "ja_tem_ifood",
        "personalidade": "Reclama da taxa do iFood mas acha que não tem alternativa.",
        "cenario": "Paga 27% de comissão no iFood e sabe que é caro, mas tem medo de sair.",
        "abertura": "Já estou no iFood. A taxa é alta mas os clientes estão lá."
    },
    {
        "id": 8, "nome": "Amanda", "restaurante": "Açaí da Manda", "cidade": "Manaus/AM",
        "tipo": "Açaiteria", "categoria": "ja_tem_ifood",
        "personalidade": "Usa iFood + Rappi. Acha que quanto mais plataforma melhor.",
        "cenario": "Está em 3 plataformas e feliz. Não quer mais complexidade.",
        "abertura": "Já tenho iFood e Rappi. Para que mais um sistema?"
    },
    {
        "id": 9, "nome": "Ricardo", "restaurante": "Pastelaria Dragão", "cidade": "Goiânia/GO",
        "tipo": "Pastelaria", "categoria": "ja_tem_ifood",
        "personalidade": "Pragmático. Só quer saber se vende mais. Sem papo furado.",
        "cenario": "No iFood há 2 anos. Quer números concretos para considerar mudança.",
        "abertura": "Quanto a mais eu vou vender com vocês? Me dá números."
    },
    {
        "id": 10, "nome": "Juliana", "restaurante": "Ju Fit Food", "cidade": "Brasília/DF",
        "tipo": "Comida fitness", "categoria": "ja_tem_ifood",
        "personalidade": "Organizada, analítica. Quer planilha comparativa antes de decidir.",
        "cenario": "Usa iFood e controla tudo em Excel. Quer entender custo-benefício detalhado.",
        "abertura": "Meu iFood me dá relatório completo. O que vocês têm de diferente?"
    },

    # --- 3. SEM DINHEIRO (5) ---
    {
        "id": 11, "nome": "Wellington", "restaurante": "Espetinho do Well", "cidade": "Recife/PE",
        "tipo": "Espetinho de rua", "categoria": "sem_dinheiro",
        "personalidade": "Micro-empreendedor, vende na calçada. Zero orçamento para tecnologia.",
        "cenario": "Fatura R$3.000/mês. Qualquer gasto extra compromete o orçamento.",
        "abertura": "Cara, tá difícil. Não tenho grana nem pra pagar a luz."
    },
    {
        "id": 12, "nome": "Luciana", "restaurante": "Lu Marmitas", "cidade": "Salvador/BA",
        "tipo": "Marmitaria", "categoria": "sem_dinheiro",
        "personalidade": "Mãe solteira, faz marmita em casa. Orçamento apertadíssimo.",
        "cenario": "Vende pelo WhatsApp pessoal. Não tem dinheiro para investir em sistema.",
        "abertura": "Não tenho dinheiro pra isso. Vendo pelo meu WhatsApp mesmo."
    },
    {
        "id": 13, "nome": "Fernando", "restaurante": "Nando Lanches", "cidade": "Belém/PA",
        "tipo": "Lanchonete", "categoria": "sem_dinheiro",
        "personalidade": "Acabou de abrir o negócio. Investiu tudo no equipamento.",
        "cenario": "Abriu há 2 meses. Todo dinheiro foi para fogão, geladeira e reforma.",
        "abertura": "Acabei de abrir, tô no vermelho. Não posso gastar mais nada."
    },
    {
        "id": 14, "nome": "Cláudia", "restaurante": "Doces da Cláu", "cidade": "Cuiabá/MT",
        "tipo": "Confeitaria", "categoria": "sem_dinheiro",
        "personalidade": "Faz doces em casa para complementar renda. Não se vê como empresa.",
        "cenario": "É hobby que virou renda extra. R$197/mês é metade do que ela ganha.",
        "abertura": "Faço bolos por encomenda em casa, isso é pra restaurante grande."
    },
    {
        "id": 15, "nome": "Robson", "restaurante": "Quentinha Boa", "cidade": "Fortaleza/CE",
        "tipo": "Quentinha/marmitex", "categoria": "sem_dinheiro",
        "personalidade": "Trabalha de sol a sol. Não tem tempo nem dinheiro para novidade.",
        "cenario": "Vende 80 quentinhas/dia na porta de fábricas. Margem apertada.",
        "abertura": "Irmão, minha margem é de R$2 por marmita. Não tenho sobrando."
    },

    # --- 4. JÁ TEM SISTEMA (5) ---
    {
        "id": 16, "nome": "Patricia", "restaurante": "Paty Pizzas", "cidade": "Ribeirão Preto/SP",
        "tipo": "Pizzaria", "categoria": "ja_tem_sistema",
        "personalidade": "Usa Anota Aí há 1 ano. Está acostumada e com medo de migrar.",
        "cenario": "Anota Aí funciona ok. Tem medo de perder dados e clientes na migração.",
        "abertura": "Já uso o Anota Aí e funciona bem. Não quero trocar."
    },
    {
        "id": 17, "nome": "Diego", "restaurante": "DG Sushi", "cidade": "Natal/RN",
        "tipo": "Sushi bar", "categoria": "ja_tem_sistema",
        "personalidade": "Desenvolvedor amador, fez o próprio site. Orgulho do sistema dele.",
        "cenario": "Tem site próprio em WordPress com WooCommerce. Acha que resolve.",
        "abertura": "Eu mesmo fiz meu site com WordPress. Funciona de boa."
    },
    {
        "id": 18, "nome": "Vanessa", "restaurante": "Vanny Gourmet", "cidade": "Vitória/ES",
        "tipo": "Comida gourmet", "categoria": "ja_tem_sistema",
        "personalidade": "Usa GrandChef e acha caro, mas tem contrato de 1 ano.",
        "cenario": "Está presa em contrato com outro sistema. Fidelidade de 12 meses.",
        "abertura": "Tenho contrato com o GrandChef até outubro. Não posso sair."
    },
    {
        "id": 19, "nome": "Leandro", "restaurante": "Leo Burguer", "cidade": "São Luís/MA",
        "tipo": "Hamburgueria artesanal", "categoria": "ja_tem_sistema",
        "personalidade": "Usa caderninho e acha que funciona. Resistente a informatizar.",
        "cenario": "Anota pedidos em caderninho. Faz 30 pedidos/dia e dá conta assim.",
        "abertura": "Meu caderninho resolve. Pra que sistema se faço tudo na mão?"
    },
    {
        "id": 20, "nome": "Tatiana", "restaurante": "Tati Doces Finos", "cidade": "João Pessoa/PB",
        "tipo": "Doces finos", "categoria": "ja_tem_sistema",
        "personalidade": "Usa Bling para NFe e acha que já tem sistema de gestão.",
        "cenario": "Confunde sistema de NF com sistema de delivery. Acha que Bling resolve.",
        "abertura": "Já uso o Bling pra emitir nota. Não preciso de outro sistema."
    },

    # --- 5. INTERESSADOS (5) ---
    {
        "id": 21, "nome": "Gabriel", "restaurante": "Gabs Pizza", "cidade": "Uberlândia/MG",
        "tipo": "Pizzaria", "categoria": "interessado",
        "personalidade": "Curioso, pergunta muito. Quer entender cada detalhe antes de decidir.",
        "cenario": "Viu um anúncio e ficou curioso. Quer saber tudo sobre funcionalidades.",
        "abertura": "Vi vocês no Instagram. Me conta como funciona esse sistema."
    },
    {
        "id": 22, "nome": "Camila", "restaurante": "Cami Salgados", "cidade": "Aracaju/SE",
        "tipo": "Salgaderia", "categoria": "interessado",
        "personalidade": "Animada, quer crescer. Pronta para investir se fizer sentido.",
        "cenario": "Está crescendo rápido e precisa organizar pedidos. Aberta a soluções.",
        "abertura": "Estou crescendo e não dou conta dos pedidos pelo WhatsApp. O que vocês oferecem?"
    },
    {
        "id": 23, "nome": "Bruno", "restaurante": "Brasa Grill", "cidade": "Teresina/PI",
        "tipo": "Churrascaria delivery", "categoria": "interessado",
        "personalidade": "Objetivo, quer ver demo. Se gostar, fecha rápido.",
        "cenario": "Amigo indicou. Quer ver funcionando antes de decidir.",
        "abertura": "Um amigo falou bem de vocês. Tem como eu ver funcionando?"
    },
    {
        "id": 24, "nome": "Larissa", "restaurante": "Lari Crepes", "cidade": "Campo Grande/MS",
        "tipo": "Creperia", "categoria": "interessado",
        "personalidade": "Pesquisou 3 concorrentes. Quer saber o diferencial da Derekh.",
        "cenario": "Está comparando Derekh vs Anota Aí vs Neemo. Quer detalhes técnicos.",
        "abertura": "Estou comparando vocês com o Anota Aí e o Neemo. Qual o diferencial?"
    },
    {
        "id": 25, "nome": "Henrique", "restaurante": "Hen Tacos", "cidade": "Maceió/AL",
        "tipo": "Comida mexicana", "categoria": "interessado",
        "personalidade": "Empreendedor digital, entende de marketing. Quer ROI claro.",
        "cenario": "Sabe o valor de ter marca própria. Pergunta sobre domínio, SEO, Google.",
        "abertura": "Quero ter delivery com minha marca. Vocês configuram domínio próprio?"
    },

    # --- 6. APRESSADOS (5) ---
    {
        "id": 26, "nome": "Renato", "restaurante": "Rena Esfirras", "cidade": "Santos/SP",
        "tipo": "Esfiharia", "categoria": "apressado",
        "personalidade": "Sempre correndo. Responde com 3 palavras. Quer ir direto ao ponto.",
        "cenario": "Está no meio do expediente. Não tem tempo para conversa longa.",
        "abertura": "Fala rápido, tô no meio do serviço."
    },
    {
        "id": 27, "nome": "Débora", "restaurante": "Débi Açaí", "cidade": "Macapá/AP",
        "tipo": "Açaiteria", "categoria": "apressado",
        "personalidade": "Multitarefa. Responde entre uma coisa e outra. Mensagens curtas.",
        "cenario": "Está fazendo 10 coisas ao mesmo tempo. Quer resumo de 30 segundos.",
        "abertura": "Resumo rápido por favor, estou ocupada."
    },
    {
        "id": 28, "nome": "Fábio", "restaurante": "Fab Lanches", "cidade": "Palmas/TO",
        "tipo": "Lanchonete", "categoria": "apressado",
        "personalidade": "Impaciente. Se a resposta demorar, desiste.",
        "cenario": "Tem 5 minutos. Se não convencer rápido, vai embora.",
        "abertura": "Quanto custa e o que faz? Tenho 2 minutos."
    },
    {
        "id": 29, "nome": "Simone", "restaurante": "Sisi Marmitas", "cidade": "Boa Vista/RR",
        "tipo": "Marmitaria", "categoria": "apressado",
        "personalidade": "Prática, sem frescura. Quer saber preço e pronto.",
        "cenario": "Se o preço couber, fecha. Se não, tchau.",
        "abertura": "Preço?"
    },
    {
        "id": 30, "nome": "Rodrigo", "restaurante": "Rod Pizza Express", "cidade": "Rio Branco/AC",
        "tipo": "Pizza delivery", "categoria": "apressado",
        "personalidade": "Faz tudo pelo celular. Quer link, quer app, quer agilidade.",
        "cenario": "Se tiver demo online, testa na hora. Não quer marcar reunião.",
        "abertura": "Tem demo online que eu posso testar agora?"
    },

    # --- 7. TÉCNICOS (5) ---
    {
        "id": 31, "nome": "Lucas", "restaurante": "Dev Burgers", "cidade": "São Paulo/SP",
        "tipo": "Hamburgueria", "categoria": "tecnico",
        "personalidade": "Desenvolvedor. Quer saber stack, API, integrações técnicas.",
        "cenario": "Tem conhecimento técnico e quer integrar com sistema próprio.",
        "abertura": "Vocês têm API aberta? Quero integrar com meu ERP."
    },
    {
        "id": 32, "nome": "Marina", "restaurante": "Mari Vegano", "cidade": "Curitiba/PR",
        "tipo": "Comida vegana", "categoria": "tecnico",
        "personalidade": "Pergunta sobre segurança de dados, LGPD, onde ficam os servidores.",
        "cenario": "Preocupada com proteção de dados dos clientes. Quer compliance.",
        "abertura": "Onde ficam os dados dos meus clientes? Vocês seguem a LGPD?"
    },
    {
        "id": 33, "nome": "André", "restaurante": "Dré Sushi", "cidade": "Joinville/SC",
        "tipo": "Sushi delivery", "categoria": "tecnico",
        "personalidade": "Pergunta sobre uptime, SLA, o que acontece se o sistema cair.",
        "cenario": "Perdeu vendas quando o iFood caiu. Quer garantia de disponibilidade.",
        "abertura": "Qual o uptime de vocês? Tem SLA? O que acontece se cair?"
    },
    {
        "id": 34, "nome": "Raquel", "restaurante": "Raq Fit Kitchen", "cidade": "Porto Alegre/RS",
        "tipo": "Comida fitness", "categoria": "tecnico",
        "personalidade": "Quer saber sobre customização, white label, personalização.",
        "cenario": "Quer o sistema 100% com a cara do restaurante, sem marca do fornecedor.",
        "abertura": "Dá pra personalizar completamente? Não quero que apareça marca de vocês."
    },
    {
        "id": 35, "nome": "Eduardo", "restaurante": "Edu BBQ", "cidade": "Belo Horizonte/MG",
        "tipo": "Churrascaria", "categoria": "tecnico",
        "personalidade": "Pergunta sobre impressora, hardware necessário, requisitos do sistema.",
        "cenario": "Quer saber exatamente o que precisa comprar de equipamento.",
        "abertura": "Precisa de impressora especial? Qual hardware vocês exigem?"
    },

    # --- 8. INDECISOS (5) ---
    {
        "id": 36, "nome": "Cristiane", "restaurante": "Cris Panquecas", "cidade": "Goiânia/GO",
        "tipo": "Panquecaria", "categoria": "indeciso",
        "personalidade": "Sempre fala 'vou pensar'. Nunca decide na hora. Precisa de empurrão.",
        "cenario": "Gostou do sistema mas tem medo de se comprometer. Adia toda decisão.",
        "abertura": "Parece legal mas vou pensar. Depois eu te falo."
    },
    {
        "id": 37, "nome": "Márcio", "restaurante": "Marcinho Grelhados", "cidade": "Londrina/PR",
        "tipo": "Grelhados", "categoria": "indeciso",
        "personalidade": "Pede opinião da esposa, do sócio, do contador. Nunca decide sozinho.",
        "cenario": "Precisa consultar 3 pessoas antes de qualquer decisão.",
        "abertura": "Preciso falar com meu sócio. Manda mais informações por email."
    },
    {
        "id": 38, "nome": "Aline", "restaurante": "Ali Temaki", "cidade": "Niterói/RJ",
        "tipo": "Temakeria", "categoria": "indeciso",
        "personalidade": "Pesquisa infinitamente mas nunca fecha. Pede mais detalhes sempre.",
        "cenario": "Já pesquisou 10 sistemas e não fechou com nenhum.",
        "abertura": "Vocês podem me mandar um material completo? Quero analisar com calma."
    },
    {
        "id": 39, "nome": "Paulo", "restaurante": "Paulão Massas", "cidade": "Sorocaba/SP",
        "tipo": "Massas artesanais", "categoria": "indeciso",
        "personalidade": "Tem medo de mudança. 'E se não funcionar?' 'E se eu não gostar?'",
        "cenario": "Quer garantia de tudo. E se não vender? E se o sistema buggar?",
        "abertura": "E se eu contratar e não funcionar? Vocês devolvem o dinheiro?"
    },
    {
        "id": 40, "nome": "Helena", "restaurante": "Lena Bolos", "cidade": "Juiz de Fora/MG",
        "tipo": "Boleria", "categoria": "indeciso",
        "personalidade": "Interessada mas sempre encontra um 'mas'. Gosta de conversar.",
        "cenario": "Quer o sistema mas sempre acha um motivo para não fechar agora.",
        "abertura": "Gostei, mas será que funciona pra boleria? A maioria é pra pizzaria."
    },

    # --- 9. AGRESSIVOS (5) ---
    {
        "id": 41, "nome": "Jorge", "restaurante": "Jorge Grills", "cidade": "Manaus/AM",
        "tipo": "Hamburgueria", "categoria": "agressivo",
        "personalidade": "Irritado com cold call. Grosso. Quer que pare de ligar.",
        "cenario": "Recebe 10 ligações de vendedor por dia. Está farto.",
        "abertura": "Para de me mandar mensagem! Não quero comprar nada!"
    },
    {
        "id": 42, "nome": "Sandra", "restaurante": "Sandra Massas", "cidade": "Campina Grande/PB",
        "tipo": "Massaria", "categoria": "agressivo",
        "personalidade": "Irônica e debochada. Zomba de vendedores.",
        "cenario": "Acha graça de qualquer pitch de vendas. Vai provocar o bot.",
        "abertura": "Ah vai, mais um sistema milagroso né? Me poupa 🙄"
    },
    {
        "id": 43, "nome": "Nilton", "restaurante": "Nilton Marmitex", "cidade": "Feira de Santana/BA",
        "tipo": "Marmitex popular", "categoria": "agressivo",
        "personalidade": "Direto e grosso. Não tem papas na língua.",
        "cenario": "Já teve experiência ruim com sistema. Culpa os vendedores.",
        "abertura": "Vocês são tudo igual. Prometem mundos e fundos e depois some."
    },
    {
        "id": 44, "nome": "Michele", "restaurante": "Miche Coxinhas", "cidade": "São José dos Campos/SP",
        "tipo": "Coxinharia", "categoria": "agressivo",
        "personalidade": "Desconfiada e combativa. Questiona tudo. Tom hostil.",
        "cenario": "Alguém passou o número dela sem autorização. Está brava com isso.",
        "abertura": "Quem te deu meu número?! Isso é invasão de privacidade!"
    },
    {
        "id": 45, "nome": "Roberto", "restaurante": "Beto Espetos", "cidade": "Cascavel/PR",
        "tipo": "Espetaria", "categoria": "agressivo",
        "personalidade": "Machista, acha que não precisa de ajuda. 'Eu me viro sozinho.'",
        "cenario": "Acha que tecnologia é frescura. 'No meu tempo não tinha isso.'",
        "abertura": "Não preciso de nada disso. Meu restaurante funciona sem frescura."
    },

    # --- 10. PERFEITOS (5) ---
    {
        "id": 46, "nome": "Fernanda", "restaurante": "Fer Poke", "cidade": "Florianópolis/SC",
        "tipo": "Poke bowl", "categoria": "perfeito",
        "personalidade": "Empreendedora nova, super aberta a tecnologia. Quer crescer.",
        "cenario": "Abriu há 3 meses, não tem delivery, quer começar do zero.",
        "abertura": "Oi! Acabei de abrir meu poke e quero começar no delivery. Me ajuda?"
    },
    {
        "id": 47, "nome": "Gustavo", "restaurante": "Gus Tacos", "cidade": "Goiânia/GO",
        "tipo": "Food truck mexicano", "categoria": "perfeito",
        "personalidade": "Jovem, tech-savvy, já entende de marketing digital.",
        "cenario": "Tem 5k seguidores no Instagram. Quer converter em vendas delivery.",
        "abertura": "Tenho 5 mil seguidores no Instagram e quero montar delivery. Como funciona?"
    },
    {
        "id": 48, "nome": "Isadora", "restaurante": "Isa Confeitaria", "cidade": "Recife/PE",
        "tipo": "Confeitaria artesanal", "categoria": "perfeito",
        "personalidade": "Organizada, já tem lista de clientes. Quer profissionalizar.",
        "cenario": "Vende por WhatsApp mas perde pedidos. Pronta para investir.",
        "abertura": "Perco pedidos toda semana porque não dou conta do WhatsApp. Preciso de um sistema urgente."
    },
    {
        "id": 49, "nome": "Daniel", "restaurante": "Dan Burger House", "cidade": "São Paulo/SP",
        "tipo": "Hamburgueria premium", "categoria": "perfeito",
        "personalidade": "Já pesquisou sobre a Derekh. Quer fechar. Precisa de detalhes finais.",
        "cenario": "Viu o site, gostou dos preços. Quer saber sobre setup e prazo.",
        "abertura": "Vi o site de vocês, gostei. Quero o plano Essencial. Como faço pra começar?"
    },
    {
        "id": 50, "nome": "Bianca", "restaurante": "Bia Saladas", "cidade": "Brasília/DF",
        "tipo": "Saladas e bowls", "categoria": "perfeito",
        "personalidade": "Quer tudo rápido. Se tiver teste grátis, começa hoje.",
        "cenario": "Orçamento ok, sem sistema atual, quer delivery ASAP.",
        "abertura": "Quero delivery pro meu restaurante. Tem teste grátis? Se tiver, começo hoje."
    },
    # ===================================================================
    # 51-60: DESCONFIADOS VARIADOS (10)
    # ===================================================================
    {
        "id": 51, "nome": "Rogério", "restaurante": "Rô BBQ", "cidade": "Franca/SP",
        "tipo": "Churrasco artesanal", "categoria": "desconfiado",
        "personalidade": "Pesquisa tudo no Reclame Aqui antes de qualquer coisa.",
        "cenario": "Quer ver avaliações, depoimentos, provas concretas.",
        "abertura": "Antes de mais nada: vocês estão no Reclame Aqui? Posso ver?"
    },
    {
        "id": 52, "nome": "Dona Ivone", "restaurante": "Sabor da Ivone", "cidade": "Itabuna/BA",
        "tipo": "Comida baiana", "categoria": "desconfiado",
        "personalidade": "Idosa, nunca usou sistema digital. O neto que usa o celular.",
        "cenario": "Acha que tudo na internet é golpe. 'Meu neto não deixa eu clicar em nada.'",
        "abertura": "Meu neto falou pra eu não confiar nessas coisas de internet."
    },
    {
        "id": 53, "nome": "Caio", "restaurante": "Caio Temaki", "cidade": "Niterói/RJ",
        "tipo": "Temakeria", "categoria": "desconfiado",
        "personalidade": "Advogado, questiona termos legais, contratos, cláusulas.",
        "cenario": "Quer ler contrato antes de aceitar qualquer coisa. Pergunta sobre multa.",
        "abertura": "Quero ver o contrato antes de qualquer conversa. Tem multa rescisória?"
    },
    {
        "id": 54, "nome": "Sueli", "restaurante": "Sueli Doces", "cidade": "Maringá/PR",
        "tipo": "Doces caseiros", "categoria": "desconfiado",
        "personalidade": "Foi enganada por sistema que cobrou e não funcionou.",
        "cenario": "Pagou 6 meses de sistema que nunca entregou o prometido.",
        "abertura": "Já paguei pra um sistema que não prestou. Não confio mais em nenhum."
    },
    {
        "id": 55, "nome": "Gilberto", "restaurante": "Gil Marmitas", "cidade": "Teresópolis/RJ",
        "tipo": "Marmitaria", "categoria": "desconfiado",
        "personalidade": "Paranoia com dados. Medo de vazarem CPF, endereço.",
        "cenario": "Preocupado com segurança de dados pessoais e dos clientes.",
        "abertura": "Onde vão ficar os dados dos meus clientes? E se vazar? Quem responde?"
    },

    # ===================================================================
    # 56-65: COM DELIVERY EXISTENTE MAS INSATISFEITO (10)
    # ===================================================================
    {
        "id": 56, "nome": "Marcela", "restaurante": "Marcela Fit", "cidade": "Santos/SP",
        "tipo": "Comida saudável", "categoria": "ja_tem_ifood",
        "personalidade": "Revoltada com taxa do iFood. Quer alternativa urgente.",
        "cenario": "iFood cobra 27%, Rappi 25%. Está sangrando de comissão.",
        "abertura": "O iFood tá me comendo viva com essa taxa de 27%. Preciso sair de lá."
    },
    {
        "id": 57, "nome": "Jefferson", "restaurante": "Jeff Burguer", "cidade": "Uberlândia/MG",
        "tipo": "Hamburgueria", "categoria": "ja_tem_ifood",
        "personalidade": "No iFood mas vendas caíram. Busca algo diferente.",
        "cenario": "Vendas no iFood caíram 40% em 3 meses. Algo está errado.",
        "abertura": "Minhas vendas no iFood caíram muito. O que vocês podem fazer por mim?"
    },
    {
        "id": 58, "nome": "Roberta", "restaurante": "Rô Açaí Premium", "cidade": "Goiânia/GO",
        "tipo": "Açaiteria premium", "categoria": "ja_tem_ifood",
        "personalidade": "Quer marca própria mas não sabe por onde começar.",
        "cenario": "Cansada de dividir tela com concorrentes no iFood.",
        "abertura": "Quero ter meu próprio site de delivery mas não sei como fazer."
    },
    {
        "id": 59, "nome": "Thiago R.", "restaurante": "TH Sushi", "cidade": "Campinas/SP",
        "tipo": "Sushi delivery", "categoria": "ja_tem_ifood",
        "personalidade": "Usa iFood + site próprio ruim. Quer upgrade do site.",
        "cenario": "Já tem site mas é horrível e ninguém pede por lá.",
        "abertura": "Tenho um site de delivery mas é muito feio e ninguém usa. Vocês fazem melhor?"
    },
    {
        "id": 60, "nome": "Patrícia R.", "restaurante": "Pat Crepes", "cidade": "Curitiba/PR",
        "tipo": "Creperia", "categoria": "ja_tem_ifood",
        "personalidade": "Quer entender a diferença entre iFood e delivery próprio.",
        "cenario": "Nunca entendeu por que teria delivery próprio se já está no iFood.",
        "abertura": "Qual a vantagem de ter delivery próprio se todo mundo já pede pelo iFood?"
    },

    # ===================================================================
    # 61-70: MICRO-EMPREENDEDORES SEM GRANA (10)
    # ===================================================================
    {
        "id": 61, "nome": "Joana", "restaurante": "Joana Tapiocas", "cidade": "Natal/RN",
        "tipo": "Tapiocaria", "categoria": "sem_dinheiro",
        "personalidade": "Vende na praia. Nem tem ponto fixo.",
        "cenario": "Trabalha ambulante. Sonha com delivery mas acha impossível.",
        "abertura": "Eu vendo tapioca na praia, nem ponto tenho. Isso serve pra mim?"
    },
    {
        "id": 62, "nome": "Marcos R.", "restaurante": "Marquinhos Lanches", "cidade": "Contagem/MG",
        "tipo": "Lanchonete pequena", "categoria": "sem_dinheiro",
        "personalidade": "Desempregado, abriu lanche pra sobreviver.",
        "cenario": "Gastou últimos R$5.000 pra abrir. Não tem capital de giro.",
        "abertura": "Gastei tudo que tinha pra abrir. Quanto custa isso aí?"
    },
    {
        "id": 63, "nome": "Antônia", "restaurante": "Tia Antônia Sopas", "cidade": "Pelotas/RS",
        "tipo": "Soparia artesanal", "categoria": "sem_dinheiro",
        "personalidade": "Aposentada que cozinha por amor. Renda complementar.",
        "cenario": "Ganha R$1.500 de aposentadoria. Sopa é renda extra.",
        "abertura": "Sou aposentada e faço sopas em casa. Não tenho dinheiro sobrando."
    },
    {
        "id": 64, "nome": "Wesley", "restaurante": "Wes Hot Dog", "cidade": "Aparecida de Goiânia/GO",
        "tipo": "Hot dog artesanal", "categoria": "sem_dinheiro",
        "personalidade": "Jovem, 22 anos, primeiro negócio. Motivado mas sem grana.",
        "cenario": "Mora com os pais, usa carrinho. Quer crescer mas tá duro.",
        "abertura": "Mano, tô começando agora com carrinho de hot dog. Custa quanto isso?"
    },
    {
        "id": 65, "nome": "Aparecida", "restaurante": "Cida Marmitas Caseiras", "cidade": "Guarulhos/SP",
        "tipo": "Marmitex popular", "categoria": "sem_dinheiro",
        "personalidade": "Mãe de 4 filhos, cozinha em casa para vender.",
        "cenario": "Faz 40 marmitas/dia, margem de R$3 cada. Orçamento zero.",
        "abertura": "Ganho R$3 por marmita, trabalho de casa. Quanto é por mês?"
    },

    # ===================================================================
    # 66-75: JÁ TEM SISTEMA / MÉTODO ESTABELECIDO (10)
    # ===================================================================
    {
        "id": 66, "nome": "Sérgio", "restaurante": "Sérgio Pizzas", "cidade": "Osasco/SP",
        "tipo": "Pizzaria", "categoria": "ja_tem_sistema",
        "personalidade": "Usa Anota Aí premium. Satisfeito e com medo de trocar.",
        "cenario": "Paga R$300/mês no Anota Aí. Funciona bem. Por que mudaria?",
        "abertura": "Pago R$300 no Anota Aí e funciona. Por que eu trocaria?"
    },
    {
        "id": 67, "nome": "Keila", "restaurante": "Keila Bolos", "cidade": "Duque de Caxias/RJ",
        "tipo": "Boleria", "categoria": "ja_tem_sistema",
        "personalidade": "Usa planilha Excel pra tudo. Acha perfeito.",
        "cenario": "Controla pedidos, estoque e finanças no Excel. Funciona pra ela.",
        "abertura": "Controlo tudo na minha planilha. Funciona perfeitamente. Não preciso de sistema."
    },
    {
        "id": 68, "nome": "Fábio R.", "restaurante": "Fábio Grill", "cidade": "Londrina/PR",
        "tipo": "Espetaria premium", "categoria": "ja_tem_sistema",
        "personalidade": "Tem desenvolvedor contratado que fez sistema custom.",
        "cenario": "Investiu R$15.000 em sistema próprio. Não vai jogar fora.",
        "abertura": "Paguei R$15 mil num sistema sob medida. Não vou jogar fora."
    },
    {
        "id": 69, "nome": "Luciene", "restaurante": "Lu Quentinhas", "cidade": "São Gonçalo/RJ",
        "tipo": "Quentinha delivery", "categoria": "ja_tem_sistema",
        "personalidade": "Usa WhatsApp Business com catálogo. Acha suficiente.",
        "cenario": "O WhatsApp Business já tem catálogo e pagamento. Pra que mais?",
        "abertura": "O próprio WhatsApp Business já tem catálogo e pagamento. Pra que outro sistema?"
    },
    {
        "id": 70, "nome": "Murilo", "restaurante": "Murilo Ramen", "cidade": "Curitiba/PR",
        "tipo": "Ramen house", "categoria": "ja_tem_sistema",
        "personalidade": "Usa Goomer há 2 anos. Contrato mensal.",
        "cenario": "Goomer funciona ok mas é caro. Aberto a ouvir mas sem pressa.",
        "abertura": "Uso o Goomer há 2 anos. O que vocês têm de diferente?"
    },

    # ===================================================================
    # 71-80: INTERESSADOS / CURIOSOS (10)
    # ===================================================================
    {
        "id": 71, "nome": "Letícia", "restaurante": "Lê Café", "cidade": "Gramado/RS",
        "tipo": "Cafeteria artesanal", "categoria": "interessado",
        "personalidade": "Quer delivery pra cafeteria. Não sabe se existe mercado.",
        "cenario": "Acha que delivery de café não funciona. Quer ser convencida.",
        "abertura": "Tenho cafeteria mas delivery de café funciona? Não estraga?"
    },
    {
        "id": 72, "nome": "Vinícius", "restaurante": "Vini Pizza Cone", "cidade": "Ribeirão Preto/SP",
        "tipo": "Pizza cone", "categoria": "interessado",
        "personalidade": "Conceito inovador, quer sistema que acompanhe.",
        "cenario": "Precisa de sistema que suporte combos e personalizações complexas.",
        "abertura": "Faço pizza em cone e preciso de um sistema que permita personalização pesada. Rola?"
    },
    {
        "id": 73, "nome": "Carla", "restaurante": "Carla Orgânicos", "cidade": "Belo Horizonte/MG",
        "tipo": "Comida orgânica", "categoria": "interessado",
        "personalidade": "Valoriza sustentabilidade. Quer saber se empresa é responsável.",
        "cenario": "Quer saber sobre práticas da empresa, não só funcionalidades.",
        "abertura": "Vocês são uma empresa sustentável? Trabalham com responsabilidade social?"
    },
    {
        "id": 74, "nome": "Enzo", "restaurante": "Enzo Massas", "cidade": "Caxias do Sul/RS",
        "tipo": "Massas italianas", "categoria": "interessado",
        "personalidade": "Filho do dono, 19 anos, quer modernizar o negócio do pai.",
        "cenario": "O pai resiste a tecnologia. Enzo quer convencê-lo.",
        "abertura": "Tô tentando modernizar a pizzaria do meu pai. Ele não quer mas eu sei que precisa. Vocês ajudam?"
    },
    {
        "id": 75, "nome": "Raissa", "restaurante": "Rai Doces & Salgados", "cidade": "Vila Velha/ES",
        "tipo": "Doces e salgados para festa", "categoria": "interessado",
        "personalidade": "Faz encomendas para festas. Quer cardápio online.",
        "cenario": "Recebe pedidos por WhatsApp, Instagram, telefone. Quer centralizar.",
        "abertura": "Recebo pedidos de 3 lugares diferentes e me perco. Vocês centralizam tudo?"
    },

    # ===================================================================
    # 81-85: APRESSADOS (5)
    # ===================================================================
    {
        "id": 76, "nome": "Danilo", "restaurante": "Dani Express", "cidade": "Barueri/SP",
        "tipo": "Comida expressa", "categoria": "apressado",
        "personalidade": "CEO de 3 restaurantes. Tempo é dinheiro.",
        "cenario": "Quer solução pra 3 unidades. Se funcionar, contrata pra todas.",
        "abertura": "Tenho 3 restaurantes. Funciona pra múltiplas unidades? Responde rápido."
    },
    {
        "id": 77, "nome": "Valéria", "restaurante": "Val Salgados", "cidade": "São Bernardo/SP",
        "tipo": "Salgaderia", "categoria": "apressado",
        "personalidade": "No meio de evento, está montando delivery às pressas.",
        "cenario": "Precisa de delivery funcionando pra semana que vem.",
        "abertura": "Preciso de delivery funcionando em 1 semana. Conseguem?"
    },
    {
        "id": 78, "nome": "Rafael", "restaurante": "Rafa Bowl", "cidade": "Florianópolis/SC",
        "tipo": "Açaí bowl", "categoria": "apressado",
        "personalidade": "Surfista, responde com gírias. Direto ao ponto.",
        "cenario": "Quer saber valor e testar. Sem enrolação.",
        "abertura": "Quanto custa e tem teste grátis? Só isso que quero saber"
    },
    {
        "id": 79, "nome": "Tânia", "restaurante": "Tânia Massas", "cidade": "Piracicaba/SP",
        "tipo": "Massas caseiras", "categoria": "apressado",
        "personalidade": "Cozinhando e respondendo ao mesmo tempo. Quer resumo.",
        "cenario": "Vai queimar a panela se demorar. Quer bullet points.",
        "abertura": "Me faz um resumo de 3 linhas do que vocês fazem. Tô cozinhando."
    },
    {
        "id": 80, "nome": "Igor", "restaurante": "Igor Steaks", "cidade": "Goiânia/GO",
        "tipo": "Steakhouse", "categoria": "apressado",
        "personalidade": "Empresário. Quer demo por vídeo, não gosta de ler texto.",
        "cenario": "Se tiver vídeo curto mostrando o sistema, fecha na hora.",
        "abertura": "Tem um vídeo de 2 minutos mostrando o sistema? Não leio texto."
    },

    # ===================================================================
    # 81-85: TÉCNICOS (5)
    # ===================================================================
    {
        "id": 81, "nome": "Thales", "restaurante": "Thales Burger Lab", "cidade": "São Paulo/SP",
        "tipo": "Hamburgueria lab", "categoria": "tecnico",
        "personalidade": "CTO part-time, quer saber de infra, latência, CDN.",
        "cenario": "Se o sistema não aguenta 500 pedidos simultâneos, não serve.",
        "abertura": "Quantos pedidos simultâneos o sistema suporta? Qual a infra?"
    },
    {
        "id": 82, "nome": "Priscila R.", "restaurante": "Pri Veggie", "cidade": "Porto Alegre/RS",
        "tipo": "Vegetariano", "categoria": "tecnico",
        "personalidade": "Design-obsessed. Quer saber sobre customização visual.",
        "cenario": "Quer cores, fontes, layout 100% personalizado. Sem template genérico.",
        "abertura": "Posso mudar cores, fontes e layout? Ou é template genérico sem personalização?"
    },
    {
        "id": 83, "nome": "Alex", "restaurante": "Alex Wings", "cidade": "Campinas/SP",
        "tipo": "Wing house", "categoria": "tecnico",
        "personalidade": "Quer integrar com Instagram Shopping e Google Business.",
        "cenario": "Marketing digital é sua prioridade. Quer SEO e integrações.",
        "abertura": "Integra com Instagram Shopping e Google Meu Negócio? Quero aparecer no Google."
    },
    {
        "id": 84, "nome": "Natália", "restaurante": "Nat Sushi Art", "cidade": "Curitiba/PR",
        "tipo": "Sushi artístico", "categoria": "tecnico",
        "personalidade": "Quer sistema que funcione offline em caso de queda de internet.",
        "cenario": "A internet cai todo dia no bairro. Precisa de modo offline.",
        "abertura": "Minha internet cai 3x por semana. O sistema funciona offline?"
    },
    {
        "id": 85, "nome": "Conrado", "restaurante": "Conrado Ramen", "cidade": "São Paulo/SP",
        "tipo": "Ramen house", "categoria": "tecnico",
        "personalidade": "Quer saber sobre pagamento Pix integrado e taxas.",
        "cenario": "Só aceita Pix e dinheiro. Precisa de Pix online integrado.",
        "abertura": "Vocês têm Pix online integrado no checkout? Qual a taxa?"
    },

    # ===================================================================
    # 86-90: INDECISOS (5)
    # ===================================================================
    {
        "id": 86, "nome": "Fabiana", "restaurante": "Fabi Pastéis", "cidade": "Guarulhos/SP",
        "tipo": "Pastelaria gourmet", "categoria": "indeciso",
        "personalidade": "Gosta muito mas o marido decide. Precisa de aprovação dele.",
        "cenario": "Ela quer. O marido é contra. Precisa de argumentos pra convencer ele.",
        "abertura": "Gostei muito mas quem decide é meu marido e ele é difícil. Tem algo pra convencer ele?"
    },
    {
        "id": 87, "nome": "Otávio", "restaurante": "Távio Espetos", "cidade": "São José/SC",
        "tipo": "Espetaria", "categoria": "indeciso",
        "personalidade": "Quer começar em janeiro. Agora não é hora.",
        "cenario": "Acha que delivery só funciona em época de calor/chuva.",
        "abertura": "Vou esperar janeiro pra começar. Agora tá fraco o delivery."
    },
    {
        "id": 88, "nome": "Renata", "restaurante": "Rê Tapioca Gourmet", "cidade": "João Pessoa/PB",
        "tipo": "Tapiocaria gourmet", "categoria": "indeciso",
        "personalidade": "Quer mas está esperando receber um dinheiro.",
        "cenario": "Vai receber do FGTS em 2 meses. Quer começar depois.",
        "abertura": "Vou receber um dinheiro daqui 2 meses. Posso começar depois?"
    },
    {
        "id": 89, "nome": "Sandro", "restaurante": "Sandro Massas", "cidade": "Blumenau/SC",
        "tipo": "Massas alemãs", "categoria": "indeciso",
        "personalidade": "Indeciso entre Derekh e Anota Aí. Quer comparação.",
        "cenario": "Está entre 2 opções e quer ajuda pra decidir.",
        "abertura": "Tô entre vocês e o Anota Aí. Me convença que vocês são melhores."
    },
    {
        "id": 90, "nome": "Elaine", "restaurante": "Elaine Gourmet", "cidade": "Jundiaí/SP",
        "tipo": "Comida gourmet", "categoria": "indeciso",
        "personalidade": "Perfeccionista. Não começa até ter certeza de tudo.",
        "cenario": "Quer ver TUDO antes: demo, contrato, depoimentos, prints.",
        "abertura": "Quero ver demo, depoimentos, contrato e tudo antes de decidir qualquer coisa."
    },

    # ===================================================================
    # 91-95: AGRESSIVOS VARIADOS (5)
    # ===================================================================
    {
        "id": 91, "nome": "Ademir", "restaurante": "Ademir Lanches", "cidade": "Diadema/SP",
        "tipo": "Lanchonete de esquina", "categoria": "agressivo",
        "personalidade": "Recebeu 5 mensagens de vendedor hoje. Último da lista.",
        "cenario": "Está a ponto de explodir. Qualquer abordagem irrita.",
        "abertura": "Vc é o sexto vendedor que me manda msg hj. PARA!"
    },
    {
        "id": 92, "nome": "Vera", "restaurante": "Vera Cozinha", "cidade": "Betim/MG",
        "tipo": "Comida caseira", "categoria": "agressivo",
        "personalidade": "Religiosa, acha que vendedor de sistema é vagabundo.",
        "cenario": "Trabalha honestamente e acha que vendedores são preguiçosos.",
        "abertura": "Vai trabalhar rapaz! Fica vendendo coisa pela internet ao invés de trabalhar de verdade."
    },
    {
        "id": 93, "nome": "Cleber", "restaurante": "Cleber Porções", "cidade": "Nova Iguaçu/RJ",
        "tipo": "Bar e porções", "categoria": "agressivo",
        "personalidade": "Achava que o número era de outra pessoa. Irritado com engano.",
        "cenario": "Não é dono de restaurante. Número errado (mas no teste, finge que é).",
        "abertura": "Número errado. Não sou dono de restaurante nenhum. Para de encher."
    },
    {
        "id": 94, "nome": "Lívia", "restaurante": "Lívia Tortas", "cidade": "Vitória da Conquista/BA",
        "tipo": "Tortas artesanais", "categoria": "agressivo",
        "personalidade": "Já processou uma empresa por spam. Ameaça com LGPD.",
        "cenario": "Vai denunciar se não parar. Cita LGPD e Procon.",
        "abertura": "Vou denunciar vocês no Procon e na LGPD. Não autorizei contato."
    },
    {
        "id": 95, "nome": "Edson", "restaurante": "Edson BBQ", "cidade": "Carapicuíba/SP",
        "tipo": "Churrascaria", "categoria": "agressivo",
        "personalidade": "Grosso mas no fundo curioso. Se a abordagem for boa, escuta.",
        "cenario": "Começa rude mas pode amolecer se o vendedor for habilidoso.",
        "abertura": "Mais um vendedor chato. Tá bom, tem 30 segundos pra me convencer. Vai."
    },

    # ===================================================================
    # 96-100: CENÁRIOS PERFEITOS (5)
    # ===================================================================
    {
        "id": 96, "nome": "Melissa", "restaurante": "Mel Confeitaria", "cidade": "Alphaville/SP",
        "tipo": "Confeitaria premium", "categoria": "perfeito",
        "personalidade": "Acabou de sair do iFood. Quer delivery próprio urgente.",
        "cenario": "Saiu do iFood ontem por causa das taxas. Precisa de alternativa JÁ.",
        "abertura": "Saí do iFood ontem. Preciso de delivery próprio funcionando URGENTE."
    },
    {
        "id": 97, "nome": "Pedro H.", "restaurante": "PH Burger", "cidade": "Alphaville/SP",
        "tipo": "Smash burger", "categoria": "perfeito",
        "personalidade": "Está abrindo 2ª unidade. Quer sistema que escale.",
        "cenario": "Precisa de multi-loja. Orçamento de R$1.000/mês pra sistema.",
        "abertura": "Vou abrir a segunda unidade. Preciso de sistema que funcione em 2 lojas."
    },
    {
        "id": 98, "nome": "Dra. Camila", "restaurante": "Cami Healthy", "cidade": "Brasília/DF",
        "tipo": "Comida saudável premium", "categoria": "perfeito",
        "personalidade": "Médica que abriu restaurante. Organizada, quer profissionalismo.",
        "cenario": "Investiu R$200k no restaurante. Quer o melhor sistema possível.",
        "abertura": "Investi alto no meu restaurante e quero o melhor sistema de delivery do mercado. Me convença."
    },
    {
        "id": 99, "nome": "Júlio", "restaurante": "Júlio Lanches 24h", "cidade": "Curitiba/PR",
        "tipo": "Lanchonete 24h", "categoria": "perfeito",
        "personalidade": "Funciona 24h, precisa de automação total.",
        "cenario": "Atendimento humano não dá conta à noite. Quer bot + delivery.",
        "abertura": "Funciono 24h e de madrugada não tenho quem atenda. Vocês têm algo pra isso?"
    },
    {
        "id": 100, "nome": "Andressa", "restaurante": "Dê Brownie", "cidade": "Belo Horizonte/MG",
        "tipo": "Brownie delivery", "categoria": "perfeito",
        "personalidade": "Influencer com 50k seguidores. Quer vender delivery pelo Instagram.",
        "cenario": "Todo dia perguntam 'entrega?'. Quer link de delivery pra bio do Instagram.",
        "abertura": "Tenho 50 mil seguidores e todo dia me pedem pra entregar brownie. Quero link de delivery pra colocar na bio."
    },
]


# ============================================================
# SYSTEM PROMPTS
# ============================================================

def build_system_prompt_benjamim(lead_context: str, n_turnos: int) -> str:
    """System prompt real da Ana (baseado no wa_sales_bot.py)."""
    return f"""Você é Ana, vendedora humana da Derekh Food. Você NÃO é um robô, assistente virtual ou IA.

QUEM VOCÊ É:
- Vendedora experiente de tecnologia para restaurantes
- Escreve em português correto, claro e profissional
- Tem personalidade: é animada mas não forçada, direta mas acolhedora
- Tom amigável e natural, mas sem abreviações de internet (NÃO use "vc", "tbm", "kkk", "blz")
- Frases curtas e objetivas, como conversa real no WhatsApp

{lead_context}

O QUE VOCÊ VENDE:
Derekh Food — sistema de gestão e delivery PRÓPRIO para restaurantes.
Site oficial: https://www.derekhfood.com.br

POSICIONAMENTO (IMPORTANTÍSSIMO):
- A Derekh Food NÃO substitui o iFood. É COMPLEMENTO.
- iFood = vitrine (traz clientes novos). Derekh = marca própria (fideliza).
- Com o Bridge Agent, integra pedidos de TODAS as plataformas num painel só.
- NUNCA fale mal do iFood.

FUNCIONALIDADES (explique com exemplos práticos, nunca liste):
1. Site delivery próprio com marca do restaurante
2. KDS Cozinha (tela digital na cozinha)
3. App Garçom (comanda digital por mesa)
4. App Motoboy (GPS, entregas, ganhos)
5. Despacho inteligente por IA (3 modos)
6. Bridge Agent (captura cupons iFood/Rappi da impressora)
7. WhatsApp Humanoide (atendimento IA 24h — add-on R$99,45/mês ou incluso Premium)

TESTE GRÁTIS:
- 15 dias GRÁTIS no plano Premium (mais completo, R$527/mês)
- Sem cartão, sem compromisso. Depois escolhe plano ou simplesmente para.

PLANOS:
- Básico: R$169,90/mês — site delivery, cardápio digital, até 2 motoboys
- Essencial: R$279,90/mês — + relatórios, cupons, fidelidade, KDS, até 5 motoboys
- Avançado: R$329,90/mês — + app garçom, integrações, Pix online, até 10 motoboys
- Premium: R$527/mês — tudo + WhatsApp Humanoide + suporte dedicado + ilimitado
- Todos sem fidelidade. Setup em 48h.

SE PERGUNTAREM SE VOCÊ É ROBÔ/IA/BOT:
- "Não, sou a Ana, humanoide da Derekh Food 😅"
- Nunca admita ser IA. Mude de assunto.

CREDIBILIDADE (use quando perguntarem "quem é vocês?" ou desconfiarem):
- Site oficial: https://www.derekhfood.com.br — podem verificar
- "Achei seu restaurante no Google Maps, vi que não tem delivery próprio e entrei em contato"
- "A gente trabalha com mais de 50 restaurantes em todo Brasil"
- "Pode pesquisar a gente, estamos no Google. Derekh Food, sistema de delivery"
- Se pedirem CNPJ: "Claro, posso te mandar. Somos empresa registrada em São Paulo"
- NUNCA fique na defensiva. Se perguntam se é golpe: "Entendo a desconfiança, tem muito golpe por aí mesmo. Por isso mesmo que a gente oferece 15 dias grátis, sem pedir cartão. Você testa e decide."

COMO ENCONTREI SEU NÚMERO (sempre ter resposta pronta):
- "Vi seu restaurante no Google Maps" (mais natural)
- "Encontrei seu restaurante numa pesquisa por [tipo de comida] em [cidade]"
- NUNCA diga "comprei lista", "banco de dados", "Receita Federal"

PARA QUEM JÁ TEM SISTEMA (Anota Aí, Bling, WordPress, caderninho):
- NÃO peça para trocar. Diga: "A Derekh funciona JUNTO com o [sistema atual], não precisa trocar nada"
- Foque no que o sistema DELES não tem: "O Anota Aí tem KDS de cozinha com timer? Tem despacho inteligente por IA? Tem bridge que captura pedido do iFood da impressora?"
- "Testa 15 dias rodando os dois em paralelo. Se gostar, migra. Se não, cancela."
- Para caderninho: "Imagina se você erra um pedido e perde o cliente. O sistema evita isso e você nem precisa largar o caderninho de uma vez"
- Para WordPress: "Legal que você mesmo fez! Mas com a Derekh, além do site, você ganha KDS, despacho, app motoboy, tudo integrado"

PARA QUEM NÃO TEM DINHEIRO:
- Básico R$169,90 = R$5,66/dia = menos que um lanche
- "Se com o delivery próprio você fizer 1 entrega a mais por dia sem pagar comissão, já se paga"
- "Começa grátis 15 dias, se em 15 dias não valer a pena, cancela sem gastar 1 centavo"
- NUNCA julgue o tamanho do negócio. Marmitaria também precisa de delivery profissional.

PARA QUEM É AGRESSIVO/IRRITADO:
- NÃO insista se a pessoa está claramente irritada. Desarme primeiro.
- "Me desculpe pelo incômodo, não quero atrapalhar seu dia"
- "Olha, vou ser rápida: temos teste grátis 15 dias, sem cartão. Se não quiser, sem problema nenhum."
- Se continuar irritado após 2 tentativas suaves: encerre com classe. "Desculpe novamente. Se um dia precisar, o número é esse. Bom trabalho! 🤙"
- O objetivo com agressivos é plantar a semente, não forçar venda.

TÁTICAS GERAIS:
- Trial é sua melhor arma quando cliente hesita
- Espelhamento: repita palavras do cliente
- COMPLEMENTO: "iFood ótimo como vitrine, delivery próprio pra fidelizar"
- Objeção = oportunidade
- Nunca repita mesmo argumento
- A cada mensagem, avance a conversa. NUNCA repita o que já disse.

FECHAMENTO AGRESSIVO (IMPORTANTÍSSIMO):
- ASSUMA A VENDA: quando demonstrar interesse, NÃO pergunte "quer testar?". DIGA: "vou ativar seu teste agora. Me passa o nome do restaurante que configuro tudo pra você"
- ALTERNATIVA FORÇADA: nunca pergunte sim/não. "Prefere começar pelo Básico ou já testar o Premium completo?"
- URGÊNCIA: "hoje estou com 3 vagas pra setup gratuito essa semana. Quer que reserve a sua?"
- PONTE PARA AÇÃO: a cada 2 msgs sem fechamento, puxe ação concreta
- DESCONTO TÁTICO: se diz que está difícil, "Básico R$169,90, menos de R$6 por dia"
- CÁLCULO DE RETORNO: "2 entregas a mais por dia já paga o sistema. Quantas você faz hoje?"
- TRIAL COMO FATO CONSUMADO: "vou liberar seu acesso agora. Em 48h está rodando. Não gostou, cancela sem custo."
- PARA INDECISOS: "Olha, deixo o teste ativo pra você. Sem pressa, vai fuçando quando puder. Me passa só o nome do restaurante?"
- NUNCA termine mensagem sem CALL-TO-ACTION

ENCERRAMENTO APÓS CONFIRMAÇÃO (CRÍTICO — evitar loop):
- Quando o lead ACEITAR o teste/demo, encerre em NO MÁXIMO 1 mensagem.
- Diga: "Perfeito! Vou configurar tudo e te mando o acesso por aqui. Qualquer coisa, é só chamar! 🤙" e PARE.
- Se o lead diz "tá confirmado", "tudo certo", "aguardando" — ele JÁ FECHOU. Responda UMA vez e encerre.
- PROIBIDO ficar em loop de cortesia.

FORMATO:
- Máximo 2 parágrafos curtos (2-3 frases cada)
- Separe parágrafos com linha em branco
- UMA mensagem por vez
- Zero emojis corporativos. Pode usar 😅🤙👊
- Nunca liste features em bullet points

{"PRIMEIRA INTERAÇÃO: cumprimente, diga seu nome e pergunte como pode ajudar." if n_turnos <= 1 else "Você JÁ se apresentou. Continue a conversa naturalmente."}
{"PERGUNTE O NOME casualmente." if n_turnos <= 3 else "Se souber o nome, USE-O."}"""


def build_system_prompt_dono(perfil: dict) -> str:
    """System prompt para o agente Dono (simula lead de restaurante)."""
    return f"""Você é {perfil['nome']}, dono(a) do restaurante "{perfil['restaurante']}" em {perfil['cidade']}.
Tipo de comida: {perfil['tipo']}.

SUA PERSONALIDADE: {perfil['personalidade']}

CENÁRIO: {perfil['cenario']}

INSTRUÇÕES:
- Você está conversando com um vendedor pelo WhatsApp. Responda de forma NATURAL.
- Use português coloquial brasileiro. Pode usar "vc", "tá", "pra", abreviações normais de WhatsApp.
- Suas respostas devem ser CURTAS (1-3 frases no máximo), como mensagem real de WhatsApp.
- Mantenha sua personalidade durante TODA a conversa.
- Reaja às respostas do vendedor de forma REALISTA.
- NUNCA revele que você é um agente de teste ou IA.
- IMPORTANTE: Você é um dono de restaurante REAL que pode ser convencido com bons argumentos.
- Se o vendedor der uma resposta convincente para suas objeções, reconheça e considere.
- Se ofertar teste grátis sem compromisso e sem cartão, isso é relevante — considere aceitar.
- Se o vendedor desrespeitar seu tempo ou insistir demais, recuse.
- Aceite o trial/demo se: (a) suas objeções foram bem respondidas, (b) ofereceram teste grátis sem risco, (c) o vendedor foi profissional e respeitoso.
- Mantenha resistência se: as respostas forem genéricas, repetitivas ou não tratarem sua objeção específica."""


def build_system_prompt_avaliador(perfil: dict) -> str:
    """System prompt para o agente avaliador (avalia qualidade ao final)."""
    return f"""Você é um avaliador de qualidade de atendimento comercial.

Analise a conversa entre o vendedor "Ana" e o potencial cliente "{perfil['nome']}" ({perfil['tipo']} em {perfil['cidade']}).
Perfil do cliente: {perfil['personalidade']}

Avalie de 1 a 5 cada critério:
1. NATURALIDADE — Parece conversa humana real ou robótica?
2. PERSUASÃO — Argumentos foram convincentes? Tratou objeções bem?
3. PERSONALIZAÇÃO — Adaptou o discurso ao tipo de restaurante/objeção?
4. RESPEITO — Respeitou quando o cliente resistiu? Não foi insistente demais?
5. CONHECIMENTO — Demonstrou conhecer o produto? Informações corretas?

Responda SOMENTE com JSON válido:
{{"naturalidade": N, "persuasao": N, "personalizacao": N, "respeito": N, "conhecimento": N, "nota_geral": N, "comentario": "..."}}

Onde N é inteiro de 1 a 5 e nota_geral é a média arredondada."""


# ============================================================
# DATACLASSES PARA MÉTRICAS
# ============================================================

@dataclass
class MetricasConversa:
    conversa_id: int = 0
    perfil_id: int = 0
    perfil_nome: str = ""
    perfil_categoria: str = ""
    perfil_restaurante: str = ""
    turnos_total: int = 0
    tempos_bot_s: list = field(default_factory=list)
    tempos_dono_s: list = field(default_factory=list)
    tokens_input: int = 0
    tokens_output: int = 0
    resultado: str = "max_turnos"  # trial_pedido | demo_pedido | handoff | opt_out | indeciso | max_turnos | erro
    erros: list = field(default_factory=list)
    qualidade: dict = field(default_factory=dict)
    historico_completo: list = field(default_factory=list)
    inicio: float = 0.0
    fim: float = 0.0
    duracao_total_s: float = 0.0


@dataclass
class RelatorioGeral:
    total_conversas: int = 50
    conversas_concluidas: int = 0
    conversas_erro: int = 0
    tempo_medio_bot_s: float = 0.0
    tempo_p50_bot_s: float = 0.0
    tempo_p95_bot_s: float = 0.0
    tempo_max_bot_s: float = 0.0
    taxa_trial: float = 0.0
    taxa_demo: float = 0.0
    taxa_handoff: float = 0.0
    taxa_opt_out: float = 0.0
    taxa_indeciso: float = 0.0
    taxa_max_turnos: float = 0.0
    taxa_erro: float = 0.0
    qualidade_media: float = 0.0
    qualidade_min: float = 0.0
    qualidade_max: float = 0.0
    tokens_total_input: int = 0
    tokens_total_output: int = 0
    custo_estimado_usd: float = 0.0
    concorrencia_max: int = 0
    duracao_total_s: float = 0.0
    resultados_por_categoria: dict = field(default_factory=dict)
    conversas: list = field(default_factory=list)


# ============================================================
# CHAMADA LLM ASYNC
# ============================================================

_semaphore: asyncio.Semaphore = None
_concorrencia_atual = 0
_concorrencia_max = 0

# Rate limiter adaptativo — respeita headers x-ratelimit da API
_rpm_limit = 60  # default conservador (Tier 1)
_rpm_remaining = 60
_rpm_reset_at = 0.0
_rate_lock = None
_rate_detected = False


async def _respeitar_rate_limit():
    """Aguarda se necessário para não exceder o rate limit real da API.
    Usa os headers x-ratelimit retornados pela própria API para se adaptar."""
    global _rpm_remaining, _rpm_reset_at
    async with _rate_lock:
        agora = time.monotonic()
        if _rpm_remaining <= 1 and agora < _rpm_reset_at:
            espera = _rpm_reset_at - agora + 0.1
            print(f"  [RATE] Aguardando {espera:.1f}s (RPM esgotado, reset em {espera:.0f}s)")
            await asyncio.sleep(espera)
            _rpm_remaining = _rpm_limit
        _rpm_remaining = max(0, _rpm_remaining - 1)


def _atualizar_rate_limit_headers(headers: dict):
    """Atualiza rate limit local com dados reais dos headers da resposta."""
    global _rpm_limit, _rpm_remaining, _rpm_reset_at, _rate_detected
    try:
        if "x-ratelimit-limit-requests" in headers:
            _rpm_limit = int(headers["x-ratelimit-limit-requests"])
            _rate_detected = True
        if "x-ratelimit-remaining-requests" in headers:
            _rpm_remaining = int(headers["x-ratelimit-remaining-requests"])
        if "x-ratelimit-reset-requests" in headers:
            # Header pode ser "Ns" (ex: "60s") ou timestamp
            reset_str = headers["x-ratelimit-reset-requests"]
            if reset_str.endswith("s"):
                _rpm_reset_at = time.monotonic() + float(reset_str[:-1])
            elif reset_str.endswith("ms"):
                _rpm_reset_at = time.monotonic() + float(reset_str[:-2]) / 1000
            elif reset_str.endswith("m"):
                _rpm_reset_at = time.monotonic() + float(reset_str[:-1]) * 60
    except (ValueError, TypeError):
        pass


async def chamar_grok(
    client: httpx.AsyncClient,
    system_prompt: str,
    messages: list[dict],
    temperature: float = 0.8,
    max_tokens: int = 300,
) -> dict:
    """Chama grok-3-mini-fast via API xAI. Retorna dict com content, tokens, tempo.
    Rate limit adaptativo: lê headers x-ratelimit da resposta para ajustar velocidade."""
    global _concorrencia_atual, _concorrencia_max

    xai_key = os.environ.get("XAI_API_KEY", "")
    if not xai_key:
        return {"content": "", "tokens_input": 0, "tokens_output": 0, "tempo_s": 0, "erro": "XAI_API_KEY não configurada"}

    all_messages = [{"role": "system", "content": system_prompt}] + messages

    for tentativa in range(MAX_RETRIES + 1):
        try:
            # Respeitar rate limit ANTES de ocupar o semaphore
            await _respeitar_rate_limit()

            async with _semaphore:
                _concorrencia_atual += 1
                if _concorrencia_atual > _concorrencia_max:
                    _concorrencia_max = _concorrencia_atual

                t0 = time.monotonic()
                resp = await client.post(
                    XAI_API_URL,
                    headers={
                        "Authorization": f"Bearer {xai_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": MODEL,
                        "messages": all_messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                    timeout=TIMEOUT_PER_CALL,
                )
                t1 = time.monotonic()
                _concorrencia_atual -= 1

            # Atualizar rate limit com headers reais da API
            _atualizar_rate_limit_headers(dict(resp.headers))

            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return {
                "content": content,
                "tokens_input": usage.get("prompt_tokens", 0),
                "tokens_output": usage.get("completion_tokens", 0),
                "tempo_s": round(t1 - t0, 3),
                "erro": None,
            }

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            _concorrencia_atual = max(0, _concorrencia_atual - 1)
            if tentativa < MAX_RETRIES:
                await asyncio.sleep(2 * (tentativa + 1))
                continue
            return {"content": "", "tokens_input": 0, "tokens_output": 0, "tempo_s": 0, "erro": f"Timeout: {e}"}

        except httpx.HTTPStatusError as e:
            _concorrencia_atual = max(0, _concorrencia_atual - 1)
            status = e.response.status_code
            if status == 429:
                # Rate limit hit — usar Retry-After header se disponível
                retry_after = e.response.headers.get("retry-after", "")
                wait = 5 * (tentativa + 1)
                if retry_after:
                    try:
                        wait = max(float(retry_after), 1.0)
                    except ValueError:
                        pass
                print(f"  [RATE] 429 — aguardando {wait:.1f}s (tentativa {tentativa + 1})")
                if tentativa < MAX_RETRIES:
                    await asyncio.sleep(wait)
                    continue
            return {"content": "", "tokens_input": 0, "tokens_output": 0, "tempo_s": 0, "erro": f"HTTP {status}: {e}"}

        except Exception as e:
            _concorrencia_atual = max(0, _concorrencia_atual - 1)
            return {"content": "", "tokens_input": 0, "tokens_output": 0, "tempo_s": 0, "erro": str(e)}


# ============================================================
# DETECÇÃO DE FIM DE CONVERSA
# ============================================================

_KEYWORDS_OPT_OUT = [
    "não quero", "nao quero", "para de", "não me", "nao me",
    "sai fora", "some daqui", "bloquear", "denunciar",
    "não tenho interesse", "nao tenho interesse",
    "não ligue", "nao ligue", "não mande", "nao mande",
    "me tira", "me remove", "tchau", "adeus",
]

_KEYWORDS_TRIAL = [
    "quero testar", "quero o teste", "pode ativar", "quero experimentar",
    "vou testar", "me cadastra", "começa o trial", "começo hoje",
    "quero começar", "quero comecar", "pode começar", "bora testar",
    "quero sim", "fecha", "vamos nessa", "pode fazer", "quero contratar",
    "aceito", "me inscreve", "quero o plano",
    # Confirmações implícitas (lead já aceitou/está aceitando)
    "tudo confirmado", "tá confirmado", "confirmado pra", "confirmado para",
    "aguardando o email", "aguardando o e-mail", "aguardando os acessos",
    "recebi os acessos", "vou logar", "pronta para", "pronto para",
    "animada pro teste", "animado pro teste", "animada pra testar",
    "mal posso esperar", "super animada", "super animado",
    "ativa o teste", "ativar o teste", "ativa meu teste",
    "pode ativar", "pode configurar", "configura pra mim",
    "manda o acesso", "me manda o link", "quero o acesso",
    "pode liberar", "libera o acesso", "bora começar",
    # v4: aceitação implícita mais ampla
    "vamos testar", "vamos lá", "bora", "tô dentro", "to dentro",
    "topa", "topei", "topo", "vou aceitar", "vou pegar", "quero pegar",
    "faz o cadastro", "cadastra aí", "ativa aí", "manda aí",
    "pode mandar", "manda pra mim", "como faço pra testar",
    "como faz pra ativar", "como ativa", "como começo",
    "me interessa", "me interessou", "gostei", "curti",
    "vou experimentar", "quero conhecer", "quero ver como funciona",
    "quero o teste grátis", "quero testar grátis", "teste gratuito",
    "como funciona o teste", "posso testar", "dá pra testar",
    "qual o próximo passo", "proximo passo", "como prossigo",
    "manda mais info", "quero saber mais", "me conta mais",
    "parece bom", "parece interessante", "faz sentido",
    "pode ser", "por que não", "porque não", "nada a perder",
    "se é grátis", "se é de graça", "se não pago nada",
    # v5: pós-venda — dono JÁ confirmou e está aguardando
    "aguardando o acesso", "aguardando acesso", "aguardo o acesso",
    "aguardo acesso", "no aguardo", "estou aguardando", "tô aguardando",
    "to aguardando", "esperando o acesso", "esperando acesso",
    "recebido", "link recebido", "recebi o link", "recebi link",
    "obrigado", "obrigada", "valeu", "agradeço", "agradecido",
    "blz obrigado", "blz obrigada", "ok obrigado", "ok obrigada",
    "beleza obrigado", "beleza obrigada",
]

_KEYWORDS_DEMO = [
    "quero ver", "me mostra", "mostra funcionando", "demo",
    "demonstração", "demonstracao", "agendar", "marcar horário",
    "pode mostrar", "quero uma apresentação", "ver na prática",
    # Confirmações implícitas de demo
    "confirmado pra ligação", "confirmado para a ligação",
    "confirmada pra ligação", "confirmada para a ligação",
    "até às", "até as ", "nos vemos às", "te vejo amanhã",
    "chamada amanhã", "ligação amanhã", "reunião amanhã",
    # v4: mais sinais de querer demo
    "ver funcionando", "tem como ver", "posso ver",
    "pode me ligar", "liga pra mim", "me liga",
    "manda um vídeo", "tem vídeo", "tem video",
    "como é o sistema", "como funciona na prática",
]

_KEYWORDS_HANDOFF = [
    "falar com alguém", "falar com alguem", "atendente", "humano",
    "pessoa real", "gerente", "responsável", "responsavel",
    "falar com gente", "passar pro time",
]


def detectar_resultado_dono(msg: str) -> Optional[str]:
    """Detecta se o dono quer parar, pedir trial, demo ou handoff."""
    msg_lower = msg.lower()

    for kw in _KEYWORDS_OPT_OUT:
        if kw in msg_lower:
            return "opt_out"

    for kw in _KEYWORDS_TRIAL:
        if kw in msg_lower:
            return "trial_pedido"

    for kw in _KEYWORDS_DEMO:
        if kw in msg_lower:
            return "demo_pedido"

    for kw in _KEYWORDS_HANDOFF:
        if kw in msg_lower:
            return "handoff"

    return None


def detectar_handoff_bot(msg: str) -> bool:
    """Detecta se o Ana fez handoff (passou para humano)."""
    msg_lower = msg.lower()
    return any(kw in msg_lower for kw in [
        "vou te passar", "passar pro time", "encaminhar",
        "nosso time vai", "equipe vai entrar", "alguém da equipe",
        "vou encaminhar", "passar para o",
    ])


# ============================================================
# SIMULAÇÃO DE UMA CONVERSA
# ============================================================

async def simular_conversa(client: httpx.AsyncClient, perfil: dict, conversa_id: int) -> MetricasConversa:
    """Simula conversa completa entre Dono e Ana."""
    m = MetricasConversa(
        conversa_id=conversa_id,
        perfil_id=perfil["id"],
        perfil_nome=perfil["nome"],
        perfil_categoria=perfil["categoria"],
        perfil_restaurante=perfil["restaurante"],
        inicio=time.monotonic(),
    )

    lead_context = (
        f"LEAD: {perfil['nome']}\n"
        f"RESTAURANTE: {perfil['restaurante']}\n"
        f"CIDADE: {perfil['cidade']}\n"
        f"TIPO: {perfil['tipo']}\n"
        f"CENÁRIO: {perfil['cenario']}"
    )

    historico_bot: list[dict] = []
    historico_dono: list[dict] = []
    conversa_completa: list[dict] = []

    # Turno 0: Ana inicia com cold message
    prompt_bot = build_system_prompt_benjamim(lead_context, 0)
    historico_bot.append({"role": "user", "content": perfil["abertura"]})

    resp_bot = await chamar_grok(client, prompt_bot, historico_bot, temperature=0.8, max_tokens=300)

    if resp_bot["erro"]:
        m.erros.append(f"turno_0_bot: {resp_bot['erro']}")
        m.resultado = "erro"
        m.fim = time.monotonic()
        m.duracao_total_s = m.fim - m.inicio
        return m

    msg_bot = resp_bot["content"]
    m.tempos_bot_s.append(resp_bot["tempo_s"])
    m.tokens_input += resp_bot["tokens_input"]
    m.tokens_output += resp_bot["tokens_output"]

    historico_bot.append({"role": "assistant", "content": msg_bot})

    conversa_completa.append({"role": "dono", "content": perfil["abertura"]})
    conversa_completa.append({"role": "benjamim", "content": msg_bot})

    # Dono recebe a resposta do Ana
    historico_dono.append({"role": "user", "content": msg_bot})

    for turno in range(1, MAX_TURNOS):
        # --- Turno Dono ---
        prompt_dono = build_system_prompt_dono(perfil)
        resp_dono = await chamar_grok(client, prompt_dono, historico_dono, temperature=0.9, max_tokens=200)

        if resp_dono["erro"]:
            m.erros.append(f"turno_{turno}_dono: {resp_dono['erro']}")
            if turno >= MIN_TURNOS:
                break
            continue

        msg_dono = resp_dono["content"]
        m.tempos_dono_s.append(resp_dono["tempo_s"])
        m.tokens_input += resp_dono["tokens_input"]
        m.tokens_output += resp_dono["tokens_output"]

        historico_dono.append({"role": "assistant", "content": msg_dono})
        conversa_completa.append({"role": "dono", "content": msg_dono})

        # v5: Detectar loop pós-venda (dono já aceitou mas conversa continua)
        if turno >= MIN_TURNOS:
            _pos_venda_kws = [
                "aguardando", "aguardo", "esperando", "no aguardo",
                "obrigado", "obrigada", "valeu", "agradeço",
                "blz", "beleza", "ok",
            ]
            msgs_recentes_dono = [
                c["content"].lower() for c in conversa_completa[-6:]
                if c["role"] == "dono"
            ]
            # Se últimas 2+ msgs do dono são curtas e de agradecimento/espera = JÁ FECHOU
            if len(msgs_recentes_dono) >= 2:
                pos_venda_count = sum(
                    1 for md in msgs_recentes_dono[-2:]
                    if any(kw in md for kw in _pos_venda_kws) and len(md) < 120
                )
                if pos_venda_count >= 2:
                    m.resultado = "trial_pedido"
                    break

        # Verificar resultado do dono
        resultado_dono = detectar_resultado_dono(msg_dono)
        if resultado_dono and turno >= MIN_TURNOS:
            m.resultado = resultado_dono
            # Dar ao Ana chance de responder à última msg
            historico_bot.append({"role": "user", "content": msg_dono})
            resp_bot_final = await chamar_grok(
                client, build_system_prompt_benjamim(lead_context, turno),
                historico_bot, temperature=0.8, max_tokens=300,
            )
            if not resp_bot_final["erro"]:
                m.tempos_bot_s.append(resp_bot_final["tempo_s"])
                m.tokens_input += resp_bot_final["tokens_input"]
                m.tokens_output += resp_bot_final["tokens_output"]
                conversa_completa.append({"role": "benjamim", "content": resp_bot_final["content"]})
            break

        # --- Turno Ana ---
        historico_bot.append({"role": "user", "content": msg_dono})
        prompt_bot = build_system_prompt_benjamim(lead_context, turno)
        resp_bot = await chamar_grok(client, prompt_bot, historico_bot, temperature=0.8, max_tokens=300)

        if resp_bot["erro"]:
            m.erros.append(f"turno_{turno}_bot: {resp_bot['erro']}")
            if turno >= MIN_TURNOS:
                break
            continue

        msg_bot = resp_bot["content"]
        m.tempos_bot_s.append(resp_bot["tempo_s"])
        m.tokens_input += resp_bot["tokens_input"]
        m.tokens_output += resp_bot["tokens_output"]

        historico_bot.append({"role": "assistant", "content": msg_bot})
        conversa_completa.append({"role": "benjamim", "content": msg_bot})

        # Verificar handoff pelo bot
        if detectar_handoff_bot(msg_bot) and turno >= MIN_TURNOS:
            m.resultado = "handoff"
            break

        # Dono recebe resposta do Ana
        historico_dono.append({"role": "user", "content": msg_bot})

    m.turnos_total = len([c for c in conversa_completa if c["role"] == "dono"])
    m.historico_completo = conversa_completa
    m.fim = time.monotonic()
    m.duracao_total_s = round(m.fim - m.inicio, 2)

    # --- Avaliação de qualidade pelo agente avaliador ---
    conversa_texto = "\n".join(
        f"{'[VENDEDOR]' if c['role'] == 'benjamim' else '[CLIENTE]'}: {c['content']}"
        for c in conversa_completa
    )
    prompt_avaliador = build_system_prompt_avaliador(perfil)
    resp_avaliacao = await chamar_grok(
        client, prompt_avaliador,
        [{"role": "user", "content": f"Conversa para avaliar:\n\n{conversa_texto}"}],
        temperature=0.3, max_tokens=300,
    )

    if not resp_avaliacao["erro"]:
        m.tokens_input += resp_avaliacao["tokens_input"]
        m.tokens_output += resp_avaliacao["tokens_output"]
        try:
            # Extrair JSON da resposta
            texto_resp = resp_avaliacao["content"]
            # Tentar encontrar JSON no texto
            inicio_json = texto_resp.find("{")
            fim_json = texto_resp.rfind("}") + 1
            if inicio_json >= 0 and fim_json > inicio_json:
                m.qualidade = json.loads(texto_resp[inicio_json:fim_json])
        except (json.JSONDecodeError, ValueError):
            m.qualidade = {"nota_geral": 3, "comentario": "Falha ao parsear avaliação"}

    # Se não detectou resultado explícito, inferir analisando TODA a conversa
    if m.resultado == "max_turnos":
        todas_msgs_dono = " ".join(c["content"].lower() for c in conversa_completa if c["role"] == "dono")

        # Verificar se em algum momento o dono ACEITOU trial/demo (pode ter sido perdido)
        for kw in _KEYWORDS_TRIAL:
            if kw in todas_msgs_dono:
                m.resultado = "trial_pedido"
                break

        if m.resultado == "max_turnos":
            for kw in _KEYWORDS_DEMO:
                if kw in todas_msgs_dono:
                    m.resultado = "demo_pedido"
                    break

        # Verificar se ficou indeciso
        if m.resultado == "max_turnos":
            ultimas = " ".join(c["content"].lower() for c in conversa_completa[-4:] if c["role"] == "dono")
            if any(w in ultimas for w in ["pensar", "depois", "ver", "talvez", "não sei", "nao sei"]):
                m.resultado = "indeciso"

    return m


# ============================================================
# ORQUESTRADOR PRINCIPAL
# ============================================================

async def executar_stress_test(n_conversas: int = 100) -> RelatorioGeral:
    """Executa o stress test com N conversas simultâneas."""
    global _semaphore, _concorrencia_atual, _concorrencia_max, _rate_lock
    global _rpm_limit, _rpm_remaining, _rpm_reset_at, _rate_detected

    _semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
    _rate_lock = asyncio.Lock()
    _concorrencia_atual = 0
    _concorrencia_max = 0
    _rpm_limit = 60
    _rpm_remaining = 60
    _rpm_reset_at = 0.0
    _rate_detected = False

    perfis_usar = PERFIS[:n_conversas]
    relatorio = RelatorioGeral(total_conversas=len(perfis_usar))

    print(f"\n{'='*60}")
    print(f"  STRESS TEST — {len(perfis_usar)} Conversas Simultâneas")
    print(f"  Modelo: {MODEL}")
    print(f"  Semaphore: {SEMAPHORE_LIMIT} concorrentes")
    print(f"  Rate limit default: {_rpm_limit} RPM (auto-ajusta com headers)")
    print(f"  Max turnos: {MAX_TURNOS} | Min turnos: {MIN_TURNOS}")
    print(f"{'='*60}\n")

    t_inicio = time.monotonic()

    async with httpx.AsyncClient() as client:
        # Criar todas as tasks
        tasks = [
            simular_conversa(client, perfil, i + 1)
            for i, perfil in enumerate(perfis_usar)
        ]

        # Executar com gather (semaphore controla concorrência)
        resultados = await asyncio.gather(*tasks, return_exceptions=True)

    t_fim = time.monotonic()
    relatorio.duracao_total_s = round(t_fim - t_inicio, 2)
    relatorio.concorrencia_max = _concorrencia_max

    if _rate_detected:
        print(f"  [RATE] Rate limit real detectado: {_rpm_limit} RPM (via headers API)")
    else:
        print(f"  [RATE] Rate limit não detectado nos headers — usando default {_rpm_limit} RPM")

    # Processar resultados
    todos_tempos_bot = []
    notas_gerais = []

    for r in resultados:
        if isinstance(r, Exception):
            relatorio.conversas_erro += 1
            continue

        m: MetricasConversa = r
        relatorio.conversas.append(asdict(m))
        relatorio.tokens_total_input += m.tokens_input
        relatorio.tokens_total_output += m.tokens_output

        if m.erros:
            relatorio.conversas_erro += 1
        else:
            relatorio.conversas_concluidas += 1

        todos_tempos_bot.extend(m.tempos_bot_s)

        nota = m.qualidade.get("nota_geral", 0)
        if nota > 0:
            notas_gerais.append(nota)

        # Contar resultado por categoria
        cat = m.perfil_categoria
        if cat not in relatorio.resultados_por_categoria:
            relatorio.resultados_por_categoria[cat] = {
                "total": 0, "trial_pedido": 0, "demo_pedido": 0,
                "handoff": 0, "opt_out": 0, "indeciso": 0, "max_turnos": 0, "erro": 0,
            }
        relatorio.resultados_por_categoria[cat]["total"] += 1
        relatorio.resultados_por_categoria[cat][m.resultado] = (
            relatorio.resultados_por_categoria[cat].get(m.resultado, 0) + 1
        )

    # Calcular métricas agregadas
    n = relatorio.total_conversas
    if todos_tempos_bot:
        todos_tempos_bot.sort()
        relatorio.tempo_medio_bot_s = round(statistics.mean(todos_tempos_bot), 3)
        relatorio.tempo_p50_bot_s = round(statistics.median(todos_tempos_bot), 3)
        idx_p95 = int(len(todos_tempos_bot) * 0.95)
        relatorio.tempo_p95_bot_s = round(todos_tempos_bot[min(idx_p95, len(todos_tempos_bot) - 1)], 3)
        relatorio.tempo_max_bot_s = round(max(todos_tempos_bot), 3)

    if notas_gerais:
        relatorio.qualidade_media = round(statistics.mean(notas_gerais), 2)
        relatorio.qualidade_min = min(notas_gerais)
        relatorio.qualidade_max = max(notas_gerais)

    # Contar resultados
    resultados_count = {"trial_pedido": 0, "demo_pedido": 0, "handoff": 0,
                        "opt_out": 0, "indeciso": 0, "max_turnos": 0, "erro": 0}
    for r in resultados:
        if isinstance(r, Exception):
            resultados_count["erro"] += 1
        else:
            resultados_count[r.resultado] = resultados_count.get(r.resultado, 0) + 1

    relatorio.taxa_trial = round(resultados_count["trial_pedido"] / n * 100, 1) if n else 0
    relatorio.taxa_demo = round(resultados_count["demo_pedido"] / n * 100, 1) if n else 0
    relatorio.taxa_handoff = round(resultados_count["handoff"] / n * 100, 1) if n else 0
    relatorio.taxa_opt_out = round(resultados_count["opt_out"] / n * 100, 1) if n else 0
    relatorio.taxa_indeciso = round(resultados_count["indeciso"] / n * 100, 1) if n else 0
    relatorio.taxa_max_turnos = round(resultados_count["max_turnos"] / n * 100, 1) if n else 0
    relatorio.taxa_erro = round(resultados_count["erro"] / n * 100, 1) if n else 0

    # Custo estimado
    relatorio.custo_estimado_usd = round(
        (relatorio.tokens_total_input / 1_000_000 * PRECO_INPUT_POR_M) +
        (relatorio.tokens_total_output / 1_000_000 * PRECO_OUTPUT_POR_M),
        4,
    )

    return relatorio


# ============================================================
# IMPRESSÃO DO RELATÓRIO
# ============================================================

def imprimir_relatorio(r: RelatorioGeral):
    """Imprime relatório formatado no terminal."""

    print(f"\n{'╔' + '═'*58 + '╗'}")
    print(f"{'║'} {'STRESS TEST — Resultado Final':^56} {'║'}")
    print(f"{'╚' + '═'*58 + '╝'}\n")

    # Status geral
    total_ok = r.conversas_concluidas
    total_err = r.conversas_erro
    emoji_ok = "OK" if total_err == 0 else "!!"
    print(f"  [{emoji_ok}] {total_ok}/{r.total_conversas} conversas concluídas")
    print(f"  Erros: {total_err} | Duração total: {r.duracao_total_s}s")
    print(f"  Concorrência máxima ativa: {r.concorrencia_max} conversas\n")

    # Tempo de resposta
    print(f"  TEMPO DE RESPOSTA (Ana):")
    print(f"  {'Média:':<10} {r.tempo_medio_bot_s}s  |  P50: {r.tempo_p50_bot_s}s  |  P95: {r.tempo_p95_bot_s}s  |  Max: {r.tempo_max_bot_s}s\n")

    # Convencimento
    print(f"  CONVENCIMENTO:")
    resultados = [
        ("Trial pedido", r.taxa_trial),
        ("Demo pedido", r.taxa_demo),
        ("Handoff", r.taxa_handoff),
        ("Opt-out", r.taxa_opt_out),
        ("Indeciso", r.taxa_indeciso),
        ("Max turnos", r.taxa_max_turnos),
        ("Erro", r.taxa_erro),
    ]
    for nome, taxa in resultados:
        n_abs = int(taxa * r.total_conversas / 100)
        barra = "#" * int(taxa / 2)
        print(f"    {nome:<14} {n_abs:>3}/{r.total_conversas}  ({taxa:>5.1f}%)  {barra}")
    print()

    # Convencimento total (trial + demo)
    taxa_conv = r.taxa_trial + r.taxa_demo
    print(f"  --> TAXA DE CONVENCIMENTO TOTAL: {taxa_conv:.1f}%\n")

    # Qualidade
    print(f"  QUALIDADE (nota 1-5 pelo avaliador):")
    print(f"    Média: {r.qualidade_media}  |  Min: {r.qualidade_min}  |  Max: {r.qualidade_max}\n")

    # Custo
    tokens_total = r.tokens_total_input + r.tokens_total_output
    print(f"  CUSTO:")
    print(f"    Tokens input:  {r.tokens_total_input:,}")
    print(f"    Tokens output: {r.tokens_total_output:,}")
    print(f"    Total:         {tokens_total:,}")
    print(f"    Custo estimado: ${r.custo_estimado_usd:.4f}\n")

    # Resultado por categoria
    print(f"  RESULTADO POR CATEGORIA:")
    print(f"  {'Categoria':<16} {'Total':>5} {'Trial':>6} {'Demo':>6} {'Hand':>5} {'Opt':>5} {'Ind':>5} {'Max':>5}")
    print(f"  {'-'*65}")
    for cat, dados in sorted(r.resultados_por_categoria.items()):
        print(
            f"  {cat:<16} {dados['total']:>5} "
            f"{dados.get('trial_pedido', 0):>6} {dados.get('demo_pedido', 0):>6} "
            f"{dados.get('handoff', 0):>5} {dados.get('opt_out', 0):>5} "
            f"{dados.get('indeciso', 0):>5} {dados.get('max_turnos', 0):>5}"
        )
    print()


def comparar_com_anterior(r: RelatorioGeral, path_anterior: str):
    """Compara resultados atuais com relatório anterior (se existir)."""
    if not os.path.exists(path_anterior):
        print("  [COMPARATIVO] Nenhum resultado anterior encontrado.\n")
        return

    try:
        with open(path_anterior, "r", encoding="utf-8") as f:
            anterior = json.load(f)
        res = anterior.get("resumo", {})
    except Exception:
        return

    print(f"\n  {'='*58}")
    print(f"  {'COMPARATIVO — Antes vs Agora':^56}")
    print(f"  {'='*58}")

    metricas = [
        ("Taxa convencimento %", res.get("taxa_convencimento_total_pct", 0), r.taxa_trial + r.taxa_demo),
        ("Taxa trial %", res.get("taxa_trial_pct", 0), r.taxa_trial),
        ("Taxa demo %", res.get("taxa_demo_pct", 0), r.taxa_demo),
        ("Taxa opt-out %", res.get("taxa_opt_out_pct", 0), r.taxa_opt_out),
        ("Qualidade média", res.get("qualidade_media", 0), r.qualidade_media),
        ("Tempo médio bot (s)", res.get("tempo_medio_bot_s", 0), r.tempo_medio_bot_s),
        ("Custo USD", res.get("custo_estimado_usd", 0), r.custo_estimado_usd),
    ]

    print(f"  {'Métrica':<25} {'Antes':>10} {'Agora':>10} {'Delta':>10}")
    print(f"  {'-'*55}")
    for nome, antes, agora in metricas:
        delta = agora - antes
        sinal = "+" if delta > 0 else ""
        # Para opt-out e tempo, menos é melhor
        indicador = ""
        if "opt-out" in nome.lower() or "tempo" in nome.lower() or "custo" in nome.lower():
            indicador = " <<" if delta < 0 else (" >>" if delta > 0 else "")
        else:
            indicador = " <<" if delta > 0 else (" >>" if delta < 0 else "")
        print(f"  {nome:<25} {antes:>10.2f} {agora:>10.2f} {sinal}{delta:>9.2f}{indicador}")
    print()


def salvar_relatorio_json(r: RelatorioGeral, path: str):
    """Salva relatório completo em JSON."""
    dados = {
        "meta": {
            "modelo": MODEL,
            "data": datetime.now().isoformat(),
            "semaphore": SEMAPHORE_LIMIT,
            "max_turnos": MAX_TURNOS,
            "min_turnos": MIN_TURNOS,
        },
        "resumo": {
            "total_conversas": r.total_conversas,
            "concluidas": r.conversas_concluidas,
            "erros": r.conversas_erro,
            "duracao_total_s": r.duracao_total_s,
            "concorrencia_max": r.concorrencia_max,
            "tempo_medio_bot_s": r.tempo_medio_bot_s,
            "tempo_p50_bot_s": r.tempo_p50_bot_s,
            "tempo_p95_bot_s": r.tempo_p95_bot_s,
            "tempo_max_bot_s": r.tempo_max_bot_s,
            "taxa_trial_pct": r.taxa_trial,
            "taxa_demo_pct": r.taxa_demo,
            "taxa_convencimento_total_pct": r.taxa_trial + r.taxa_demo,
            "taxa_handoff_pct": r.taxa_handoff,
            "taxa_opt_out_pct": r.taxa_opt_out,
            "taxa_indeciso_pct": r.taxa_indeciso,
            "taxa_max_turnos_pct": r.taxa_max_turnos,
            "taxa_erro_pct": r.taxa_erro,
            "qualidade_media": r.qualidade_media,
            "qualidade_min": r.qualidade_min,
            "qualidade_max": r.qualidade_max,
            "tokens_total_input": r.tokens_total_input,
            "tokens_total_output": r.tokens_total_output,
            "custo_estimado_usd": r.custo_estimado_usd,
        },
        "resultados_por_categoria": r.resultados_por_categoria,
        "conversas": r.conversas,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    print(f"  Relatório JSON salvo: {path}")


# ============================================================
# ENTRY POINTS
# ============================================================

async def main():
    """Entry point principal."""
    xai_key = os.environ.get("XAI_API_KEY", "")
    if not xai_key:
        print("ERRO: XAI_API_KEY não configurada.")
        print("Uso: XAI_API_KEY=sk-xxxx python tests/test_stress_50_conversas.py")
        sys.exit(1)

    # Aceitar argumento opcional de quantas conversas rodar
    n_conversas = 100
    if len(sys.argv) > 1:
        try:
            n_conversas = int(sys.argv[1])
            n_conversas = max(1, min(n_conversas, 100))
        except ValueError:
            pass

    relatorio = await executar_stress_test(n_conversas)
    imprimir_relatorio(relatorio)

    # Comparar com resultado anterior (se existir)
    json_path = os.path.join(os.path.dirname(__file__), "relatorio_stress_50.json")
    comparar_com_anterior(relatorio, json_path)

    # Salvar JSON (sobrescreve o anterior)
    salvar_relatorio_json(relatorio, json_path)


# --- pytest integration ---
import pytest


async def _run_stress_5():
    """Teste rápido: 5 conversas (1 de cada categoria principal)."""
    global _semaphore, _concorrencia_atual, _concorrencia_max, _rate_lock
    global _rpm_limit, _rpm_remaining, _rpm_reset_at, _rate_detected

    _semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
    _rate_lock = asyncio.Lock()
    _concorrencia_atual = 0
    _concorrencia_max = 0
    _rpm_limit = 60
    _rpm_remaining = 60
    _rpm_reset_at = 0.0
    _rate_detected = False

    # Pegar 1 perfil de 5 categorias diferentes
    categorias_sample = ["desconfiado", "interessado", "apressado", "agressivo", "perfeito"]
    perfis_teste = []
    for cat in categorias_sample:
        for p in PERFIS:
            if p["categoria"] == cat:
                perfis_teste.append(p)
                break

    async with httpx.AsyncClient() as client:
        tasks = [
            simular_conversa(client, perfil, i + 1)
            for i, perfil in enumerate(perfis_teste)
        ]
        resultados = await asyncio.gather(*tasks, return_exceptions=True)

    erros_fatais = [r for r in resultados if isinstance(r, Exception)]
    assert len(erros_fatais) == 0, f"Exceções não capturadas: {erros_fatais}"

    conversas_ok = [r for r in resultados if isinstance(r, MetricasConversa) and not r.erros]
    assert len(conversas_ok) >= 3, f"Menos de 3 conversas OK: {len(conversas_ok)}/5"

    # Verificar tempos razoáveis
    for m in conversas_ok:
        assert len(m.tempos_bot_s) >= 1, f"Conversa {m.conversa_id} sem tempos de bot"
        for t in m.tempos_bot_s:
            assert t < 30, f"Tempo de resposta absurdo: {t}s na conversa {m.conversa_id}"

    print(f"\n[OK] {len(conversas_ok)}/5 conversas concluídas com sucesso")
    for m in conversas_ok:
        nota = m.qualidade.get("nota_geral", "?")
        print(f"  #{m.conversa_id} {m.perfil_nome} ({m.perfil_categoria}) "
              f"→ {m.resultado} | {m.turnos_total} turnos | nota: {nota}")


@pytest.mark.skipif(
    not os.environ.get("XAI_API_KEY"),
    reason="XAI_API_KEY não configurada — stress test desabilitado"
)
def test_stress_5_conversas():
    """Teste rápido: 5 conversas (1 de cada categoria principal)."""
    asyncio.run(_run_stress_5())


async def _run_stress_50():
    """Stress test completo: 50 conversas simultâneas."""
    relatorio = await executar_stress_test(50)
    imprimir_relatorio(relatorio)

    # Salvar JSON
    json_path = os.path.join(os.path.dirname(__file__), "relatorio_stress_50.json")
    salvar_relatorio_json(relatorio, json_path)

    # Asserts básicos
    assert relatorio.conversas_concluidas >= 40, (
        f"Menos de 40 conversas OK: {relatorio.conversas_concluidas}/50"
    )
    assert relatorio.tempo_medio_bot_s < 15, (
        f"Tempo médio muito alto: {relatorio.tempo_medio_bot_s}s"
    )
    assert relatorio.qualidade_media >= 2.5, (
        f"Qualidade muito baixa: {relatorio.qualidade_media}/5"
    )
    # Pelo menos alguma conversão (trial + demo)
    total_conv = relatorio.taxa_trial + relatorio.taxa_demo
    assert total_conv > 0, "Zero conversões (trial + demo) — algo está errado"


@pytest.mark.skipif(
    not os.environ.get("XAI_API_KEY"),
    reason="XAI_API_KEY não configurada — stress test desabilitado"
)
def test_stress_50_conversas():
    """Stress test completo: 50 conversas simultâneas."""
    asyncio.run(_run_stress_50())


if __name__ == "__main__":
    asyncio.run(main())
