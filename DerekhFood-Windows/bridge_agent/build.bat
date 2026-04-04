@echo off
cd /d "%~dp0.."
echo ========================================
echo Derekh Food - Build Bridge Agent
echo ========================================
echo.

:: Instalar dependencias
pip install pyinstaller
pip install pywin32 pystray Pillow requests

:: Build com PyInstaller
pyinstaller --noconfirm --onefile --console ^
    --name "DerekhFood-Bridge" ^
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
    --hidden-import pystray ^
    --hidden-import PIL ^
    bridge_agent\__main__.py

echo.
echo Build completo! Executavel em: dist\DerekhFood-Bridge.exe
pause
