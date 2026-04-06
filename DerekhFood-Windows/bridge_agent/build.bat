@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0.."
echo ========================================
echo Derekh Food - Build Bridge Agent
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
if exist dist\DerekhFood-Bridge.exe del /q dist\DerekhFood-Bridge.exe

:: Build com PyInstaller
:: --paths . : adiciona DerekhFood-Windows\ ao sys.path (bridge_agent vira package)
:: --windowed : SEM janela de console (roda invisivel, apenas tray icon)
:: --onefile : gera um unico .exe autocontido
pyinstaller --noconfirm --onefile --windowed ^
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
    bridge_agent\__main__.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Build falhou!
    pause
    exit /b 1
)

:: Verificar que o .exe foi gerado
if not exist "dist\DerekhFood-Bridge.exe" (
    echo.
    echo [ERRO] Build aparentemente completou mas dist\DerekhFood-Bridge.exe nao existe!
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Build completo!
echo  Executavel: dist\DerekhFood-Bridge.exe
echo ============================================
pause
