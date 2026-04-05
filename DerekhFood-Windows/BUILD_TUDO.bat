@echo off
chcp 65001 >nul 2>&1
title Derekh Food - Build Tudo (Bridge + Impressora)
color 0B

echo.
echo  +--------------------------------------------------+
echo  ^|        DEREKH FOOD - Build Tudo                 ^|
echo  ^|                                                  ^|
echo  ^|  Este script builda os 2 executaveis:           ^|
echo  ^|    1. DerekhFood-Bridge.exe                     ^|
echo  ^|    2. DerekhFood-Impressora.exe                 ^|
echo  ^|                                                  ^|
echo  ^|  Os .exe gerados sao AUTOCONTIDOS                ^|
echo  ^|  (nao precisam de Python instalado)              ^|
echo  +--------------------------------------------------+
echo.

cd /d "%~dp0"

:: -- 1. Python + deps do projeto (auto-instala se ausente) ---
echo  [1/4] Verificando Python + dependencias do projeto...
call "%~dp0_CHECK_DEPS.bat"
if %ERRORLEVEL% NEQ 0 (
    echo  [ERRO] Nao foi possivel configurar o ambiente.
    pause
    exit /b 1
)

:: -- 2. Instalar PyInstaller (so para build) ------------------
echo.
echo  [2/4] Instalando PyInstaller...
pip install pyinstaller --quiet
if %ERRORLEVEL% NEQ 0 (
    echo  [ERRO] Falha ao instalar PyInstaller.
    pause
    exit /b 1
)
echo         PyInstaller pronto.

:: -- 3. Build Bridge Agent ------------------------------------
echo.
echo  [3/4] Buildando DerekhFood-Bridge.exe...
echo         Isso pode levar 1-2 minutos.
call "%~dp0bridge_agent\build.bat"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERRO] Build do Bridge falhou!
    pause
    exit /b 1
)
if not exist "%~dp0dist\DerekhFood-Bridge.exe" (
    echo.
    echo  [ERRO] Build do Bridge completou mas o .exe nao foi gerado!
    pause
    exit /b 1
)
echo         OK: dist\DerekhFood-Bridge.exe criado.

:: -- 4. Build Printer Agent -----------------------------------
echo.
echo  [4/4] Buildando DerekhFood-Impressora.exe...
echo         Isso pode levar 1-2 minutos.
call "%~dp0printer_agent\build.bat"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERRO] Build do Printer falhou!
    pause
    exit /b 1
)
if not exist "%~dp0dist\DerekhFood-Impressora.exe" (
    echo.
    echo  [ERRO] Build do Printer completou mas o .exe nao foi gerado!
    pause
    exit /b 1
)
echo         OK: dist\DerekhFood-Impressora.exe criado.

:: -- Resumo final ---------------------------------------------
echo.
echo  +--------------------------------------------------+
echo  ^|            BUILD COMPLETO!                       ^|
echo  +--------------------------------------------------+
echo.
echo  Executaveis gerados em "%~dp0dist\":
echo    - DerekhFood-Bridge.exe
echo    - DerekhFood-Impressora.exe
echo.

:: Mostra tamanho dos .exe gerados
for %%f in ("%~dp0dist\DerekhFood-Bridge.exe") do echo    Bridge     : %%~zf bytes
for %%f in ("%~dp0dist\DerekhFood-Impressora.exe") do echo    Impressora : %%~zf bytes

echo.
echo  Proximos passos:
echo    1. Copie a pasta dist\ (com os 2 .exe)
echo    2. Distribua junto com: INSTALAR.bat, SERVIDOR.bat,
echo       BRIDGE.bat, IMPRESSAO.bat, SIMULAR.bat, TUDO.bat
echo       + pasta virtual_printer\ (para a impressora virtual)
echo.
pause
