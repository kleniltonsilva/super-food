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
    powershell -ExecutionPolicy Bypass -File "%~dp0impressora_virtual\install.ps1"
) else (
    echo  [INFO] Abrindo PowerShell como Administrador...
    echo         Aceite a permissao na janela que aparecer.
    echo.
    powershell -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0impressora_virtual\install.ps1\"' -Verb RunAs -Wait"
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
echo  Agora voce pode usar os 3 programas:
echo.
echo    1. SERVIDOR.bat    - Liga a impressora virtual
echo    2. SIMULAR.bat     - Envia pedidos fake pelo spooler
echo    3. BRIDGE.bat      - Intercepta e envia para o backend
echo    4. IMPRESSAO.bat   - Recebe pedidos reais e imprime
echo.
echo  Ordem para testar:
echo    1. Abra SERVIDOR.bat (deixe rodando)
echo    2. Abra BRIDGE.bat (deixe rodando)
echo    3. Abra SIMULAR.bat (dispara pedidos)
echo    4. Veja o Bridge interceptar e processar!
echo.

pause
