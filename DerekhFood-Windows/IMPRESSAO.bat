@echo off
chcp 65001 >nul 2>&1
title Derekh Food - Impressao de Pedidos
color 0C

echo.
echo  Iniciando Printer Agent (Impressao de Pedidos)...
echo  Na primeira vez, uma janela de configuracao aparecera.
echo  (Mantenha esta janela aberta!)
echo.

cd /d "%~dp0"
python -m printer_agent

pause
