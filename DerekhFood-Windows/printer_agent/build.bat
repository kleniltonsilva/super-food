@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0.."
echo ========================================
echo Derekh Food - Build Agente Impressora
echo ========================================
echo.

:: ── Python + dependencias do projeto (auto-instala se ausente) ────────────
call "%~dp0..\_CHECK_DEPS.bat"
if %ERRORLEVEL% NEQ 0 (
    echo  [ERRO] Nao foi possivel configurar o ambiente.
    pause
    exit /b 1
)

:: Instalar PyInstaller (exclusivo de build)
echo.
echo [INFO] Instalando PyInstaller...
pip install pyinstaller --quiet

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
    --hidden-import win32timezone ^
    --hidden-import win32con ^
    --hidden-import pywintypes ^
    --hidden-import pystray ^
    --hidden-import pystray._win32 ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.ImageDraw ^
    --hidden-import requests ^
    --hidden-import requests.adapters ^
    --hidden-import urllib3 ^
    --hidden-import charset_normalizer ^
    --hidden-import certifi ^
    --hidden-import idna ^
    --hidden-import websockets ^
    --hidden-import websockets.client ^
    --hidden-import websockets.legacy ^
    --hidden-import websockets.legacy.client ^
    --hidden-import websockets.exceptions ^
    printer_agent\__main__.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Build falhou!
    pause
    exit /b 1
)

:: Verificar que o .exe foi gerado
if not exist "dist\DerekhFood-Impressora.exe" (
    echo.
    echo [ERRO] Build aparentemente completou mas dist\DerekhFood-Impressora.exe nao existe!
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Build completo!
echo  Executavel: dist\DerekhFood-Impressora.exe
echo ============================================
pause
