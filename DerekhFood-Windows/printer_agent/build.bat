@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0.."
echo ========================================
echo Derekh Food - Build Agente Impressora
echo ========================================
echo.

:: Instalar dependencias
pip install pyinstaller --quiet
pip install pywin32 pystray Pillow requests websockets --quiet

:: Limpar build anterior
if exist build rmdir /s /q build
if exist dist\DerekhFood-Impressora.exe del /q dist\DerekhFood-Impressora.exe

:: Build com PyInstaller
:: --paths . : adiciona DerekhFood-Windows\ ao sys.path (printer_agent vira package)
:: --windowed : SEM janela de console (roda invisivel, apenas tray icon)
:: --onefile : gera um unico .exe autocontido
pyinstaller --noconfirm --onefile --windowed ^
    --name "DerekhFood-Impressora" ^
    --paths . ^
    --hidden-import printer_agent ^
    --hidden-import printer_agent.main ^
    --hidden-import printer_agent.config ^
    --hidden-import printer_agent.api_client ^
    --hidden-import printer_agent.ws_client ^
    --hidden-import printer_agent.print_driver ^
    --hidden-import printer_agent.print_formatter ^
    --hidden-import printer_agent.print_queue ^
    --hidden-import printer_agent.ui ^
    --hidden-import printer_agent.ui.config_window ^
    --hidden-import printer_agent.ui.tray_icon ^
    --hidden-import win32print ^
    --hidden-import win32api ^
    --hidden-import win32security ^
    --hidden-import pystray ^
    --hidden-import pystray._win32 ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.ImageDraw ^
    --hidden-import requests ^
    --hidden-import websockets ^
    --hidden-import websockets.client ^
    --hidden-import websockets.legacy ^
    --hidden-import websockets.legacy.client ^
    printer_agent\__main__.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Build falhou!
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Build completo!
echo  Executavel: dist\DerekhFood-Impressora.exe
echo ============================================
pause
