#!/usr/bin/env python3
"""
Script de Inicialização do Banco de Dados - Super Food SaaS

Este é um wrapper simples que chama o sistema centralizado
em database/init.py

Uso:
    python init_database.py              # Inicializa tudo
    python init_database.py --reset      # Reseta banco (CUIDADO!)
    python init_database.py --seed-only  # Apenas seeds
    python init_database.py --schema-only # Apenas tabelas

Para mais opções, veja: python -m database.init --help
"""

import sys
import os

# Adiciona raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.init import init_database, reset_database


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
        from database.init import run_seeds_only
        run_seeds_only()
        sys.exit(0)

    if "--schema-only" in args:
        from database.init import create_schema_only
        create_schema_only()
        sys.exit(0)

    # Padrão: inicializa tudo
    init_database()
