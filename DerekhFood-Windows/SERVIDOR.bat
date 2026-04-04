@echo off
chcp 65001 >nul 2>&1
title Derekh Food - Impressora Virtual (TCP 9100)
color 0A

echo.
echo  Iniciando servidor da impressora virtual na porta 9100...
echo  (Mantenha esta janela aberta!)
echo.

cd /d "%~dp0"

:: ── Verificar Python ──────────────────────────────────────────
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [ERRO] Python nao encontrado! Rode INSTALAR.bat primeiro.
    pause
    exit /b 1
)

:: ── Instalar dependencias automaticamente ─────────────────────
echo  [INFO] Verificando dependencias...
pip install pywin32 --quiet 2>nul
echo  [OK] Dependencias verificadas.
echo.

python -m virtual_printer server --output "%~dp0virtual_printer\output"

pause
