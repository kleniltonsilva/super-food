@echo off
chcp 65001 >nul 2>&1
title Derekh Food - Simulador de Pedidos
color 0E

echo.
echo  =============================================
echo    SIMULADOR DE PEDIDOS - Derekh Food
echo  =============================================
echo.
echo  Opcoes:
echo    1. Enviar 1 pedido de CADA plataforma (4 total)
echo    2. Enviar 5 pedidos iFood
echo    3. Enviar 5 pedidos Rappi
echo    4. Enviar 5 pedidos 99Food
echo    5. Enviar 5 pedidos Uber Eats
echo    6. Bombardeio! 10 pedidos de cada (40 total)
echo    7. Personalizado
echo.

set /p OPCAO="  Escolha (1-7): "

cd /d "%~dp0"

:: ── Verificar Python ──────────────────────────────────────────
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [ERRO] Python nao encontrado! Rode INSTALAR.bat primeiro.
    pause
    exit /b 1
)

:: ── Instalar dependencias automaticamente ─────────────────────
pip install pywin32 --quiet 2>nul

if "%OPCAO%"=="1" (
    python -m virtual_printer simulate
) else if "%OPCAO%"=="2" (
    python -m virtual_printer simulate --platform ifood -n 5 --interval 2
) else if "%OPCAO%"=="3" (
    python -m virtual_printer simulate --platform rappi -n 5 --interval 2
) else if "%OPCAO%"=="4" (
    python -m virtual_printer simulate --platform 99food -n 5 --interval 2
) else if "%OPCAO%"=="5" (
    python -m virtual_printer simulate --platform ubereats -n 5 --interval 2
) else if "%OPCAO%"=="6" (
    python -m virtual_printer simulate -n 10 --interval 1
) else if "%OPCAO%"=="7" (
    set /p PLAT="  Plataforma (ifood/rappi/99food/ubereats/todas): "
    set /p QTD="  Quantidade por plataforma: "
    set /p INT="  Intervalo em segundos: "
    if "!PLAT!"=="todas" (
        python -m virtual_printer simulate -n !QTD! --interval !INT!
    ) else (
        python -m virtual_printer simulate --platform !PLAT! -n !QTD! --interval !INT!
    )
) else (
    echo  Opcao invalida!
)

echo.
pause
