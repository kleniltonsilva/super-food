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
python -m bridge_agent

pause
