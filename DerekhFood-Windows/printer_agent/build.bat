@echo off
echo ========================================
echo Derekh Food - Build Agente Impressora
echo ========================================

REM Instalar dependencias
pip install -r requirements.txt

REM Build com PyInstaller
pyinstaller --onefile --windowed --icon=assets/icon.ico --name "DerekhFood-Impressora" main.py

echo.
echo Build completo! Executavel em: dist\DerekhFood-Impressora.exe
pause
