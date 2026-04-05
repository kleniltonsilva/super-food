@echo off
chcp 65001 >nul 2>&1
title Derekh Food - Bridge Agent (Interceptador)
color 0D

echo.
echo  Iniciando Bridge Agent (Interceptador de Pedidos)...
echo  Na primeira vez, uma janela de configuracao aparecera.
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
pip install requests pywin32 pystray Pillow --quiet 2>nul
echo  [OK] Dependencias verificadas.
echo.

python -m bridge_agent %*

pause
