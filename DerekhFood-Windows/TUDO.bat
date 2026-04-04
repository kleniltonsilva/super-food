@echo off
chcp 65001 >nul 2>&1
title Derekh Food - Iniciar Tudo
color 0F

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║      DEREKH FOOD - Iniciar Tudo                  ║
echo  ║                                                   ║
echo  ║  Abre 3 janelas em sequencia:                     ║
echo  ║    1. Servidor (impressora virtual TCP 9100)       ║
echo  ║    2. Bridge (interceptador de pedidos)            ║
echo  ║    3. Impressao (recebe pedidos e imprime)         ║
echo  ╚══════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: ── Verificar Python ──────────────────────────────────────────
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [ERRO] Python nao encontrado! Rode INSTALAR.bat primeiro.
    pause
    exit /b 1
)

:: ── 1. Servidor (impressora virtual) ───────────────────────────
echo  [1/3] Abrindo SERVIDOR (impressora virtual)...
start "Derekh Food - Servidor TCP 9100" cmd /c "%~dp0SERVIDOR.bat"

:: Aguardar 3 segundos para o servidor TCP subir
echo         Aguardando servidor iniciar (3s)...
timeout /t 3 /nobreak >nul

:: ── 2. Bridge (interceptador) ──────────────────────────────────
echo  [2/3] Abrindo BRIDGE (interceptador)...
start "Derekh Food - Bridge Agent" cmd /c "%~dp0BRIDGE.bat"

:: Aguardar 3 segundos
timeout /t 3 /nobreak >nul

:: ── 3. Impressao (printer agent) ──────────────────────────────
echo  [3/3] Abrindo IMPRESSAO (printer agent)...
start "Derekh Food - Impressao" cmd /c "%~dp0IMPRESSAO.bat"

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║  Tudo iniciado! 3 janelas abertas.                ║
echo  ║                                                   ║
echo  ║  Para testar: abra SIMULAR.bat em outra janela    ║
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  (Pode fechar esta janela)
pause
