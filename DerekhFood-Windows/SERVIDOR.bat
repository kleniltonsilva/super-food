@echo off
chcp 65001 >nul 2>&1
title Derekh Food - Impressora Virtual (TCP 9100)
color 0A

echo.
echo  Iniciando servidor da impressora virtual na porta 9100...
echo  (Mantenha esta janela aberta!)
echo.

cd /d "%~dp0"

:: ── Python + todas as dependencias (auto-instala se ausente) ───────────────
call "%~dp0_CHECK_DEPS.bat"
if %ERRORLEVEL% NEQ 0 (
    echo  [ERRO] Nao foi possivel configurar o ambiente.
    pause
    exit /b 1
)
echo.

python -m virtual_printer server --output "%~dp0virtual_printer\output"

pause
