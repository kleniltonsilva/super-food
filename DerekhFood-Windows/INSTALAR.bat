@echo off
chcp 65001 >nul 2>&1
title Derekh Food - Instalador Windows
color 0B

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║      DEREKH FOOD - Instalador Windows           ║
echo  ║                                                  ║
echo  ║  Este script instala tudo que voce precisa:      ║
echo  ║    1. Python 3.12 (se nao tiver)                 ║
echo  ║    2. Dependencias (pywin32, etc)                 ║
echo  ║    3. Impressora Termica Virtual                  ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: ── Verificar Python ────────────────────────────────────────────────────────

echo  [1/4] Verificando Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  PYTHON NAO ENCONTRADO!
    echo.
    echo  Voce precisa instalar o Python primeiro:
    echo    1. Acesse: https://www.python.org/downloads/
    echo    2. Baixe Python 3.12 ou superior
    echo    3. IMPORTANTE: Marque "Add Python to PATH" na instalacao!
    echo    4. Depois rode este script novamente
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo         Python %PYVER% encontrado - OK

:: ── Instalar dependencias ────────────────────────────────────────────────────

echo.
echo  [2/4] Instalando dependencias Python...
echo         (pywin32, pystray, Pillow, requests, websockets)
echo.

pip install pywin32>=306 pystray>=0.12 Pillow>=10.0 requests>=2.31 websockets>=12.0 --quiet 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo  [AVISO] Algumas dependencias podem ter falhado. Tentando individualmente...
    pip install pywin32 --quiet 2>nul
    pip install pystray --quiet 2>nul
    pip install Pillow --quiet 2>nul
    pip install requests --quiet 2>nul
    pip install websockets --quiet 2>nul
)
echo         Dependencias instaladas - OK

:: ── Instalar impressora virtual ──────────────────────────────────────────────

echo.
echo  [3/4] Instalando impressora "Termica Virtual 80mm"...
echo         (Requer permissao de Administrador)
echo.

:: Verificar se ja esta rodando como admin
net session >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    powershell -ExecutionPolicy Bypass -File "%~dp0virtual_printer\install.ps1"
) else (
    echo  [INFO] Abrindo PowerShell como Administrador...
    echo         Aceite a permissao na janela que aparecer.
    echo.
    powershell -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0virtual_printer\install.ps1\"' -Verb RunAs -Wait"
)

:: ── Resultado ────────────────────────────────────────────────────────────────

echo.
echo  [4/4] Verificando instalacao...

python -c "import win32print; print('         pywin32 OK')" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo  [ERRO] pywin32 falhou. Tente: pip install pywin32
)

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║           INSTALACAO CONCLUIDA!                  ║
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  Agora voce pode usar os programas:
echo.
echo    TUDO.bat           - Inicia tudo (servidor+bridge+impressao)
echo    SERVIDOR.bat       - Liga a impressora virtual
echo    BRIDGE.bat         - Intercepta e envia para o backend
echo    IMPRESSAO.bat      - Recebe pedidos reais e imprime
echo    SIMULAR.bat        - Envia pedidos fake pelo spooler
echo.
echo  Jeito mais facil de testar:
echo    1. Clique em TUDO.bat (abre 3 janelas automaticamente)
echo    2. Configure Bridge e Impressao na primeira vez
echo    3. Abra SIMULAR.bat para disparar pedidos de teste
echo    4. Veja o Bridge interceptar, criar pedido e imprimir!
echo.
echo  DICA: Bridge e Impressao podem iniciar com o Windows
echo        (marque "Iniciar com Windows" na configuracao)
echo.

pause
