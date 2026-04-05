@echo off
chcp 65001 >nul 2>&1
title Derekh Food - Instalador Windows
color 0B

echo.
echo  +--------------------------------------------------+
echo  ^|      DEREKH FOOD - Instalador Windows           ^|
echo  ^|                                                  ^|
echo  ^|  Este script instala tudo que voce precisa:     ^|
echo  ^|    1. Python 3.12 (baixa e instala sozinho)     ^|
echo  ^|    2. Dependencias (pywin32, etc)                ^|
echo  ^|    3. Impressora Termica Virtual                 ^|
echo  +--------------------------------------------------+
echo.

:: ── 1+2. Python + TODAS as dependencias (auto-instala se ausente) ──────────
echo  [1/4] Verificando Python + dependencias...
call "%~dp0_CHECK_DEPS.bat"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERRO] Nao foi possivel configurar o ambiente.
    pause
    exit /b 1
)
echo  [2/4] Dependencias OK.

:: ── Instalar impressora virtual ──────────────────────────────────────────────

echo.
echo  [3/4] Instalando impressora "Termica Virtual 80mm"...
echo         (Requer permissao de Administrador)
echo.

:: Verificar se ja esta rodando como admin
net session >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    powershell -ExecutionPolicy Bypass -File "%~dp0virtual_printer\install.ps1"
    set "PS_EXIT=%ERRORLEVEL%"
) else (
    echo  [INFO] Abrindo PowerShell como Administrador...
    echo         Aceite a permissao UAC na janela que aparecer.
    echo.
    powershell -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0virtual_printer\install.ps1\"' -Verb RunAs -Wait"
    set "PS_EXIT=0"
)

:: ── Resultado ────────────────────────────────────────────────────────────────

echo.
echo  [4/4] Verificando instalacao...

python -c "import win32print; print('         pywin32 OK')" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo  [ERRO] pywin32 falhou. Tente: pip install pywin32
    pause
    exit /b 1
)

:: Verificar que a impressora EXISTE de verdade no Windows
python -c "import win32print; lst=[p[2] for p in win32print.EnumPrinters(2|4)]; exit(0 if 'Termica Virtual 80mm' in lst else 1)" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ═══════════════════════════════════════════════════════════
    echo   [FALHA] Impressora "Termica Virtual 80mm" NAO foi instalada!
    echo  ═══════════════════════════════════════════════════════════
    echo.
    echo   Impressoras atualmente no seu Windows:
    python -c "import win32print; [print('     - '+p[2]) for p in win32print.EnumPrinters(2^|4)]" 2>nul
    echo.
    echo   Possiveis causas:
    echo     1. Voce NAO aceitou o UAC de Administrador
    echo     2. Driver "Generic / Text Only" nao disponivel neste Windows
    echo     3. PowerShell bloqueado por politica
    echo.
    echo   SOLUCAO MANUAL:
    echo     Abra PowerShell como Administrador e cole:
    echo.
    echo       cd "%~dp0virtual_printer"
    echo       Set-ExecutionPolicy -Scope Process Bypass -Force
    echo       .\install.ps1
    echo.
    echo   Leia as mensagens de erro para diagnosticar.
    echo.
    pause
    exit /b 1
)
echo         Impressora "Termica Virtual 80mm" detectada - OK

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
