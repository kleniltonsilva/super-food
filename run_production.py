#!/usr/bin/env python3
"""
Super Food - Script de Produção
Executa todos os serviços do sistema de forma profissional.

Para SaaS escalável com 1000+ restaurantes:
- FastAPI + Uvicorn como backend principal (stateless, escalável)
- Streamlit apenas para admin interno

Uso:
    python run_production.py              # Inicia todos os serviços
    python run_production.py --api-only   # Apenas API FastAPI
    python run_production.py --admin-only # Apenas Super Admin Streamlit
"""

import subprocess
import sys
import os
import signal
import time
from pathlib import Path

# Configuração dos serviços
SERVICES = {
    "api": {
        "name": "FastAPI Backend",
        "command": [
            "uvicorn", "backend.app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",  # Modo desenvolvimento (remove para prod e adiciona --workers 4)
        ],
        "essential": True,
        "description": "API REST + WebSockets (principal)"
    },
    "admin": {
        "name": "Super Admin",
        "command": [
            "streamlit", "run", "streamlit_app/super_admin.py",
            "--server.port=8501",
            "--server.headless=true",
            "--server.runOnSave=false",
            "--browser.gatherUsageStats=false",
        ],
        "essential": False,
        "description": "Dashboard administrativo SaaS"
    },
    "restaurante": {
        "name": "Dashboard Restaurante",
        "command": [
            "streamlit", "run", "streamlit_app/restaurante_app.py",
            "--server.port=8502",
            "--server.headless=true",
            "--server.runOnSave=false",
            "--browser.gatherUsageStats=false",
        ],
        "essential": False,
        "description": "Painel do restaurante (migrar para FastAPI)"
    },
    "motoboy": {
        "name": "App Motoboy",
        "command": [
            "streamlit", "run", "app_motoboy/motoboy_app.py",
            "--server.port=8503",
            "--server.headless=true",
            "--server.runOnSave=false",
            "--browser.gatherUsageStats=false",
        ],
        "essential": False,
        "description": "PWA Motoboy (migrar para FastAPI)"
    },
}

processes = {}


def start_service(service_id: str) -> subprocess.Popen:
    """Inicia um serviço específico"""
    service = SERVICES[service_id]
    print(f"🚀 Iniciando {service['name']}...")
    print(f"   Comando: {' '.join(service['command'])}")

    # Usar subprocess.DEVNULL para evitar bloqueio do buffer de pipe
    # start_new_session=True cria um novo grupo de processos (daemon)
    process = subprocess.Popen(
        service["command"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=Path(__file__).parent,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
        start_new_session=True  # Permite que subprocessos sobrevivam ao script pai
    )

    return process


def stop_all():
    """Para todos os serviços"""
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
    """Handler para Ctrl+C"""
    stop_all()
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 60)
    print("🍕 SUPER FOOD - Sistema de Produção")
    print("=" * 60)

    # Parse argumentos
    api_only = "--api-only" in sys.argv
    admin_only = "--admin-only" in sys.argv

    services_to_start = []

    if api_only:
        services_to_start = ["api"]
        print("\n📡 Modo: Apenas API FastAPI")
    elif admin_only:
        services_to_start = ["admin"]
        print("\n🔧 Modo: Apenas Super Admin")
    else:
        services_to_start = list(SERVICES.keys())
        print("\n🌐 Modo: Todos os serviços")

    print("\nServiços a iniciar:")
    for sid in services_to_start:
        s = SERVICES[sid]
        print(f"  • {s['name']}: {s['description']}")

    print("\n" + "-" * 60)

    # Iniciar serviços
    for service_id in services_to_start:
        try:
            processes[service_id] = start_service(service_id)
            time.sleep(2)  # Aguardar inicialização
        except Exception as e:
            print(f"❌ Erro ao iniciar {service_id}: {e}")
            if SERVICES[service_id]["essential"]:
                stop_all()
                sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ Sistema iniciado!")
    print("=" * 60)
    print("\n📍 Endpoints disponíveis:")

    if "api" in services_to_start:
        print("   • API FastAPI:      http://localhost:8000")
        print("   • API Docs:         http://localhost:8000/docs")
        print("   • Site Cliente:     http://localhost:8000/cliente/{codigo}")
        print("   • Site Legado:      http://localhost:8000/site/{codigo}")
        print("   • WebSocket:        ws://localhost:8000/ws/{restaurante_id}")

    if "admin" in services_to_start:
        print("   • Super Admin:      http://localhost:8501")

    if "restaurante" in services_to_start:
        print("   • Restaurante:      http://localhost:8502")

    if "motoboy" in services_to_start:
        print("   • App Motoboy:      http://localhost:8503")

    print("\n💡 Pressione Ctrl+C para parar todos os serviços")
    print("-" * 60)

    # Monitorar processos
    while True:
        for name, process in list(processes.items()):
            if process.poll() is not None:
                print(f"⚠️  Serviço '{name}' parou inesperadamente!")
                if SERVICES[name]["essential"]:
                    print("🔄 Reiniciando serviço essencial...")
                    processes[name] = start_service(name)
        time.sleep(5)


if __name__ == "__main__":
    main()
