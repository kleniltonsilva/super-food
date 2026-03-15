#!/usr/bin/env python3
"""
Super Food v4.0 - Script de Produção
Executa a API FastAPI que serve todos os apps React.

Apps disponíveis (servidos pela FastAPI na porta 8000):
  - Painel Restaurante:  http://localhost:8000/admin
  - Super Admin:         http://localhost:8000/superadmin
  - App Motoboy (PWA):   http://localhost:8000/entregador
  - Site Cliente:        http://localhost:8000/cliente/{codigo}

Uso:
    python run_production.py         # Inicia API + serve React
    python run_production.py --prod  # Modo produção (sem --reload, 4 workers)
"""

import subprocess
import sys
import os
import signal
import time
from pathlib import Path

processes = {}


def start_api(prod_mode: bool = False) -> subprocess.Popen:
    if prod_mode:
        command = [
            "gunicorn", "backend.app.main:app",
            "--worker-class", "uvicorn.workers.UvicornWorker",
            "--workers", "4",
            "--host", "0.0.0.0",
            "--port", "8000",
        ]
        print("🚀 Iniciando FastAPI (modo produção, 4 workers)...")
    else:
        command = [
            "uvicorn", "backend.app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
        ]
        print("🚀 Iniciando FastAPI (modo desenvolvimento)...")

    print(f"   Comando: {' '.join(command)}")
    return subprocess.Popen(
        command,
        cwd=Path(__file__).parent,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
        start_new_session=True,
    )


def stop_all():
    print("\n🛑 Parando todos os serviços...")
    for name, process in processes.items():
        if process.poll() is None:
            process.terminate()
            print(f"   Parado: {name}")
    time.sleep(2)
    for name, process in processes.items():
        if process.poll() is None:
            process.kill()


def signal_handler(sig, frame):
    stop_all()
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    prod_mode = "--prod" in sys.argv

    print("=" * 60)
    print("🍕 DEREKH FOOD v4.0 - Sistema de Produção")
    print("=" * 60)
    print()

    processes["api"] = start_api(prod_mode)

    print()
    print("=" * 60)
    print("✅ Sistema iniciado!")
    print("=" * 60)
    print()
    print("📍 Endpoints:")
    print("   • Painel Admin:    http://localhost:8000/admin")
    print("   • Super Admin:     http://localhost:8000/superadmin")
    print("   • App Motoboy:     http://localhost:8000/entregador")
    print("   • Site Cliente:    http://localhost:8000/cliente/{codigo}")
    print("   • API Docs:        http://localhost:8000/docs")
    print("   • WebSocket:       ws://localhost:8000/ws/{restaurante_id}")
    print()
    print("🔑 Credenciais padrão:")
    print("   • Super Admin:     superadmin / SuperFood2025!")
    print("   • Restaurantes:    teste-{tipo}@superfood.test / 123456")
    print()
    print("💡 Pressione Ctrl+C para parar")
    print("-" * 60)

    while True:
        if processes["api"].poll() is not None:
            print("⚠️  FastAPI parou inesperadamente! Reiniciando...")
            processes["api"] = start_api(prod_mode)
        time.sleep(5)


if __name__ == "__main__":
    main()
