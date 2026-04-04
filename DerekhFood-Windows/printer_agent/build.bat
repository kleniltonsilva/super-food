@echo off
cd /d "%~dp0.."
echo ========================================
echo Derekh Food - Build Agente Impressora
echo ========================================
echo.

:: Instalar dependencias
pip install pyinstaller
pip install pywin32 pystray Pillow requests websockets

:: Build com PyInstaller
pyinstaller --noconfirm --onefile --console ^
    --name "DerekhFood-Impressora" ^
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
    --hidden-import pystray ^
    --hidden-import PIL ^
    --hidden-import websockets ^
    printer_agent\__main__.py

echo.
echo Build completo! Executavel em: dist\DerekhFood-Impressora.exe
pause
