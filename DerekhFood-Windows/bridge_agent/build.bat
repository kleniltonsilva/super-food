@echo off
REM Build DerekhFood-Bridge.exe com PyInstaller
REM Executar na raiz do projeto: bridge_agent\build.bat

echo === Derekh Food Bridge Agent — Build ===
echo.

pip install pyinstaller
pip install -r bridge_agent\requirements.txt

pyinstaller --noconfirm --onefile --windowed ^
    --name "DerekhFood-Bridge" ^
    --icon "bridge_agent\ui\icon.ico" ^
    --add-data "bridge_agent\ui;ui" ^
    --hidden-import win32print ^
    --hidden-import win32api ^
    --hidden-import pystray ^
    --hidden-import PIL ^
    bridge_agent\main.py

echo.
echo Build concluído! Executável em dist\DerekhFood-Bridge.exe
pause
