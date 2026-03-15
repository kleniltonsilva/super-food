#!/usr/bin/env python3
"""
Ponto de entrada único para inicialização do banco de dados.

Derekh Food SaaS - Sistema de Inicialização de Dados

Uso via linha de comando:
    python -m database.init              # Inicializa tudo
    python -m database.init --seed-only  # Apenas popula dados
    python -m database.init --schema-only # Apenas cria tabelas
    python -m database.init --reset      # Reseta banco (PERIGOSO)

Uso via código:
    from database.init import init_database
    init_database()
"""

import sys
import os

# Adiciona raiz ao path para imports corretos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.session import engine, SessionLocal, init_db
from database.base import Base
from database.seed import run_all_seeds


def run_db_upgrade(verbose: bool = True) -> bool:
    """
    Executa upgrade do banco (adiciona colunas faltantes).

    Usa database/db_upgrade.py para garantir que todas as colunas
    existem, mesmo em bancos criados antes de atualizações.
    """
    try:
        from database.db_upgrade import upgrade_database
        if verbose:
            print("\n🔧 Verificando colunas faltantes...")
        upgrade_database()
        return True
    except ImportError:
        if verbose:
            print("  ⏭️  db_upgrade.py não encontrado, pulando")
        return False
    except Exception as e:
        if verbose:
            print(f"  ⚠️  Erro no upgrade: {e}")
        return False


def init_database(
    create_schema: bool = True,
    run_seeds: bool = True,
    run_upgrade: bool = True,
    verbose: bool = True
) -> dict:
    """
    Inicializa o banco de dados de forma centralizada.

    Args:
        create_schema: Se True, cria todas as tabelas
        run_seeds: Se True, executa scripts de seed
        run_upgrade: Se True, executa db_upgrade para colunas faltantes
        verbose: Se True, exibe logs de progresso

    Returns:
        Dict com resultados da inicialização
    """
    results = {
        'schema_created': False,
        'upgrade_executed': False,
        'seeds_executed': {},
        'errors': []
    }

    try:
        # 1. Criar schema (tabelas)
        if create_schema:
            if verbose:
                print("\n" + "=" * 60)
                print("🚀 INICIALIZANDO BANCO DE DADOS - SUPER FOOD")
                print("=" * 60)
                print("\n📦 Criando schema (tabelas)...")

            init_db()
            results['schema_created'] = True

            if verbose:
                print("✅ Schema criado com sucesso!")

        # 1.5. Executar upgrade (colunas faltantes)
        if run_upgrade:
            results['upgrade_executed'] = run_db_upgrade(verbose)

        # 2. Executar seeds
        if run_seeds:
            if verbose:
                print("\n🌱 Executando seeds...")

            session = SessionLocal()
            try:
                seed_results = run_all_seeds(session, verbose=verbose)
                results['seeds_executed'] = seed_results
            finally:
                session.close()

            if verbose:
                print("\n✅ Seeds executados com sucesso!")

        # Resumo final
        if verbose:
            print("\n" + "=" * 60)
            print("✅ BANCO DE DADOS PRONTO!")
            print("=" * 60)
            print("\n📝 CREDENCIAIS DE TESTE:")
            print("   Super Admin: superadmin / SuperFood2025!")
            print("   Restaurante: teste@superfood.com / 123456")
            print("\n🚀 Execute: streamlit run streamlit_app/super_admin.py")
            print("=" * 60 + "\n")

    except Exception as e:
        results['errors'].append(str(e))
        if verbose:
            print(f"\n❌ Erro durante inicialização: {e}")
        raise

    return results


def reset_database(confirm: bool = False, verbose: bool = True) -> bool:
    """
    Reseta o banco de dados (PERIGOSO - apenas desenvolvimento).

    Args:
        confirm: Deve ser True para confirmar a operação
        verbose: Se True, exibe logs

    Returns:
        True se resetado com sucesso
    """
    if not confirm:
        if verbose:
            print("❌ Operação cancelada. Use confirm=True para confirmar.")
        return False

    try:
        if verbose:
            print("\n⚠️  RESETANDO BANCO DE DADOS...")
            print("   Isso irá APAGAR todos os dados!")

        # Dropar todas as tabelas
        Base.metadata.drop_all(bind=engine)

        if verbose:
            print("   ✅ Tabelas removidas")

        # Recriar tudo
        init_database(verbose=verbose)

        return True

    except Exception as e:
        if verbose:
            print(f"❌ Erro ao resetar: {e}")
        return False


def create_schema_only(verbose: bool = True) -> bool:
    """
    Cria apenas o schema (tabelas), sem popular dados.

    Útil para ambientes de produção onde os dados
    serão inseridos de outra forma.
    """
    try:
        init_database(create_schema=True, run_seeds=False, verbose=verbose)
        return True
    except Exception:
        return False


def run_seeds_only(verbose: bool = True) -> dict:
    """
    Executa apenas os seeds, sem criar schema.

    Útil quando as tabelas já existem e você quer
    apenas popular dados iniciais.
    """
    return init_database(create_schema=False, run_seeds=True, verbose=verbose)


# Execução via linha de comando
if __name__ == "__main__":
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print(__doc__)
        sys.exit(0)

    if "--reset" in args:
        resposta = input("⚠️  ATENÇÃO: Isso apagará TODOS os dados. Continuar? (sim/não): ")
        if resposta.lower() == "sim":
            reset_database(confirm=True)
        else:
            print("Operação cancelada.")
        sys.exit(0)

    if "--seed-only" in args:
        run_seeds_only()
        sys.exit(0)

    if "--schema-only" in args:
        create_schema_only()
        sys.exit(0)

    # Padrão: inicializa tudo
    init_database()
