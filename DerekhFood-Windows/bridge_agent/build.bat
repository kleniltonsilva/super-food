@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0.."
echo ========================================
echo Derekh Food - Build Bridge Agent
echo ========================================
echo.

:: Instalar dependencias
pip install pyinstaller --quiet
pip install pywin32 pystray Pillow requests --quiet

:: Limpar build anterior
if exist build rmdir /s /q build
if exist dist\DerekhFood-Bridge.exe del /q dist\DerekhFood-Bridge.exe

:: Build com PyInstaller
:: --paths . : adiciona DerekhFood-Windows\ ao sys.path (bridge_agent vira package)
:: --console : mantem janela de terminal visivel (facilita debug)
:: --onefile : gera um unico .exe autocontido
pyinstaller --noconfirm --onefile --console ^
    --name "DerekhFood-Bridge" ^
    --paths . ^
    --hidden-import bridge_agent ^
    --hidden-import bridge_agent.main ^
    --hidden-import bridge_agent.config ^
    --hidden-import bridge_agent.bridge_client ^
    --hidden-import bridge_agent.spooler_monitor ^
    --hidden-import bridge_agent.text_extractor ^
    --hidden-import bridge_agent.simulador ^
    --hidden-import bridge_agent.ui ^
    --hidden-import bridge_agent.ui.config_window ^
    --hidden-import win32print ^
    --hidden-import win32api ^
    --hidden-import win32security ^
    --hidden-import pystray ^
    --hidden-import pystray._win32 ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.ImageDraw ^
    --hidden-import requests ^
    bridge_agent\__main__.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Build falhou!
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Build completo!
echo  Executavel: dist\DerekhFood-Bridge.exe
echo ============================================
pause
