@echo off
chcp 65001 >nul 2>&1
title Derekh Food - Impressora Virtual (TCP 9100)
color 0A

echo.
echo  Iniciando servidor da impressora virtual na porta 9100...
echo  (Mantenha esta janela aberta!)
echo.

cd /d "%~dp0"
python -m virtual_printer server --output "%~dp0virtual_printer\output"

pause
