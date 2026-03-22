"""
Seed auxiliar: Remove restaurantes demo existentes para permitir
recriação com dados atualizados (variações, imagens, etc).

Uso: python -m database.seed.seed_012_reset_demos
Depois: python -m database.seed.seed_011_restaurantes_por_tipo
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./super_food.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def main():
    print(f"Conectando ao banco: {DATABASE_URL[:50]}...")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Encontra restaurantes demo
    result = db.execute(text(
        "SELECT id, nome_fantasia, email, codigo_acesso FROM restaurantes WHERE email LIKE '%@superfood.test'"
    ))
    demos = result.fetchall()

    if not demos:
        print("Nenhum restaurante demo encontrado.")
        db.close()
        return

    print(f"\nEncontrados {len(demos)} restaurantes demo:")
    for d in demos:
        print(f"  ID={d[0]} | {d[1]} | {d[2]} | código={d[3]}")

    ids = [d[0] for d in demos]
    ids_str = ",".join(str(i) for i in ids)

    # Deletar em ordem (respeitando FKs) usando CASCADE onde possível
    # O modelo Restaurante tem cascade em vários relacionamentos, mas
    # para garantir em todos os BDs, deletamos explicitamente
    tabelas_dependentes = [
        "variacoes_produto",  # depende de produtos
        "itens_pedido",  # depende de pedidos e produtos
        "combo_itens",  # depende de combos e produtos
        "entregas",  # depende de pedidos
        "pedidos_cozinha",  # depende de pedidos (se existir)
        "carrinhos",
        "pedidos",
        "produtos",
        "categorias_menu",
        "combos",
        "config_restaurante",
        "site_config",
        "bairros_entrega",
        "cozinheiros",
        "config_cozinha",
        "clientes",
        "enderecos_cliente",
        "motoboys",
    ]

    print(f"\nRemovendo dados associados...")
    for tabela in tabelas_dependentes:
        try:
            if tabela == "variacoes_produto":
                # Variações são ligadas a produtos, não diretamente a restaurante
                db.execute(text(f"""
                    DELETE FROM {tabela} WHERE produto_id IN (
                        SELECT id FROM produtos WHERE restaurante_id IN ({ids_str})
                    )
                """))
            elif tabela == "itens_pedido":
                db.execute(text(f"""
                    DELETE FROM {tabela} WHERE pedido_id IN (
                        SELECT id FROM pedidos WHERE restaurante_id IN ({ids_str})
                    )
                """))
            elif tabela == "combo_itens":
                db.execute(text(f"""
                    DELETE FROM {tabela} WHERE combo_id IN (
                        SELECT id FROM combos WHERE restaurante_id IN ({ids_str})
                    )
                """))
            elif tabela == "entregas":
                db.execute(text(f"""
                    DELETE FROM {tabela} WHERE pedido_id IN (
                        SELECT id FROM pedidos WHERE restaurante_id IN ({ids_str})
                    )
                """))
            elif tabela == "pedidos_cozinha":
                db.execute(text(f"""
                    DELETE FROM {tabela} WHERE pedido_id IN (
                        SELECT id FROM pedidos WHERE restaurante_id IN ({ids_str})
                    )
                """))
            elif tabela == "enderecos_cliente":
                db.execute(text(f"""
                    DELETE FROM {tabela} WHERE cliente_id IN (
                        SELECT id FROM clientes WHERE restaurante_id IN ({ids_str})
                    )
                """))
            else:
                db.execute(text(f"DELETE FROM {tabela} WHERE restaurante_id IN ({ids_str})"))
            print(f"  ✓ {tabela}")
        except Exception as e:
            print(f"  ⚠ {tabela}: {e}")
            db.rollback()
            continue

    # Deletar restaurantes
    db.execute(text(f"DELETE FROM restaurantes WHERE id IN ({ids_str})"))
    db.commit()

    print(f"\n✅ {len(demos)} restaurantes demo removidos com sucesso!")
    print("Agora rode: python -m database.seed.seed_011_restaurantes_por_tipo")

    db.close()


if __name__ == "__main__":
    main()
