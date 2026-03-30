@echo off
chcp 65001 >nul 2>&1
title Derekh Food - Desinstalar Impressora Virtual
color 0C

echo.
echo  Removendo impressora "Termica Virtual 80mm"...
echo.

net session >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    powershell -ExecutionPolicy Bypass -File "%~dp0virtual_printer\uninstall.ps1"
) else (
    powershell -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0virtual_printer\uninstall.ps1\"' -Verb RunAs -Wait"
)

echo.
pause
