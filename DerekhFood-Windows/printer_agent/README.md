# Derekh Food — Agente de Impressão

Agente Windows que conecta via WebSocket ao backend para receber pedidos em tempo real e imprimir comandas em impressoras térmicas.

## Requisitos

- Windows 10/11
- Python 3.10+ (para desenvolvimento)
- Impressora térmica 80mm ou 58mm (ESC/POS compatível)

## Instalação (Desenvolvimento)

```bash
cd printer_agent
pip install -r requirements.txt
python main.py
```

## Build (Executável)

```bash
cd printer_agent
build.bat
```

O executável será gerado em `dist/DerekhFood-Impressora.exe`.

## Instalação (Usuário Final)

1. Baixe `DerekhFood-Impressora.exe`
2. Execute o programa
3. Na janela de configuração:
   - Informe o endereço do servidor (ex: `wss://superfood-api.fly.dev`)
   - Faça login com email e senha do restaurante
   - Selecione a(s) impressora(s) por setor
4. O agente ficará na bandeja do sistema (system tray)
5. Marque "Iniciar com Windows" para auto-start

## Arquitetura

```
main.py           → Orquestrador
ws_client.py      → WebSocket com reconnect exponencial
api_client.py     → REST client (GET /print-data)
print_queue.py    → SQLite fila + idempotência
print_formatter.py → Gerar bytes ESC/POS
print_driver.py   → win32print RAW mode
ui/tray_icon.py   → System tray (pystray)
ui/config_window.py → Login + config (tkinter)
```

## Dados armazenados

- Config: `%APPDATA%/DerekhFood/printer_config.json`
- Fila: `%APPDATA%/DerekhFood/print_queue.db`
- Logs: `%APPDATA%/DerekhFood/logs/YYYY-MM-DD.log`

## Setores de Impressão

Cada categoria de produto pode ser associada a um setor:
- **Geral** — impressora padrão
- **Cozinha** — pratos quentes, pizzas
- **Bar** — bebidas
- **Caixa** — recibo completo com valores

Se apenas uma impressora está configurada, todos os itens vão para ela.
Se múltiplas estão configuradas, os itens são separados por setor.
