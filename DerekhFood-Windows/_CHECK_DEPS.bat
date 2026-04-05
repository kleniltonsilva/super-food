@echo off
:: ============================================================
::  _CHECK_DEPS.bat
::  Helper mestre - garante Python + TODAS as dependencias.
::
::  Uso (nos outros .bat):
::      call "%~dp0_CHECK_DEPS.bat"
::      if %ERRORLEVEL% NEQ 0 exit /b 1
::
::  O que faz:
::    1. Chama _CHECK_PYTHON.bat (baixa/instala Python 3.12)
::    2. Verifica se todas as deps do requirements.txt estao OK
::    3. Se faltar algo, instala via pip (modo silencioso)
::    4. Usa arquivo .deps_ok como cache (nao reinstala toda vez)
::
::  NAO usa 'setlocal' para propagar PATH do Python ao pai.
:: ============================================================

:: -- 1. Python ------------------------------------------------
call "%~dp0_CHECK_PYTHON.bat"
if %ERRORLEVEL% NEQ 0 exit /b 1

:: -- 2. Cache: se ja foi verificado nesta sessao/dia, pular ---
:: O arquivo .deps_ok fica em %APPDATA%\DerekhBridge\ e guarda
:: a ultima verificacao. Evita rodar "pip install" toda vez.
set "DEPS_CACHE_DIR=%APPDATA%\DerekhBridge"
set "DEPS_CACHE_FILE=%DEPS_CACHE_DIR%\.deps_ok"

if not exist "%DEPS_CACHE_DIR%" mkdir "%DEPS_CACHE_DIR%" >nul 2>&1

:: Se o cache existe E foi criado hoje, pular verificacao
if exist "%DEPS_CACHE_FILE%" (
    :: Verifica se o cache tem menos de 1 dia
    forfiles /p "%DEPS_CACHE_DIR%" /m ".deps_ok" /d 0 >nul 2>&1
    if not errorlevel 1 (
        :: Cache valido - pular instalacao
        echo  [OK] Dependencias ja verificadas hoje ^(cache^).
        exit /b 0
    )
)

:: -- 3. Validar deps instaladas -------------------------------
echo  [INFO] Verificando dependencias Python...

:: Teste rapido: tenta importar todos os modulos criticos
python -c "import win32print, pystray, PIL, requests, websockets" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo  [OK] Todas as dependencias ja instaladas.
    :: Atualiza cache
    echo OK> "%DEPS_CACHE_FILE%"
    exit /b 0
)

:: -- 4. Faltam deps - instalar --------------------------------
echo  [INFO] Instalando dependencias do requirements.txt...
echo         Isso pode levar 1-2 minutos na primeira vez.
echo.

:: Atualiza pip primeiro (silencioso, sem falhar se der erro)
python -m pip install --upgrade pip --quiet 2>nul

:: Instala do requirements.txt unificado
if exist "%~dp0requirements.txt" (
    pip install -r "%~dp0requirements.txt" --quiet
    set "PIP_RESULT=%ERRORLEVEL%"
) else (
    :: Fallback: instala pacote por pacote (caso o requirements.txt esteja faltando)
    :: IMPORTANTE: version specs com >= precisam estar entre aspas para CMD nao interpretar > como redirect
    echo  [AVISO] requirements.txt nao encontrado, instalando pacotes individualmente...
    pip install "pywin32>=306" --quiet 2>nul
    pip install "pystray>=0.19.5" --quiet 2>nul
    pip install "Pillow>=10.0.0" --quiet 2>nul
    pip install "requests>=2.31.0" --quiet 2>nul
    pip install "websockets>=12.0" --quiet 2>nul
    set "PIP_RESULT=0"
)

:: -- 5. Validar que funcionou ---------------------------------
python -c "import win32print, pystray, PIL, requests, websockets" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERRO] Algumas dependencias nao instalaram corretamente.
    echo.
    echo  Tente rodar manualmente:
    echo    pip install -r "%~dp0requirements.txt"
    echo.
    echo  Se pywin32 falhar, pode precisar rodar pos-install:
    echo    python "%LOCALAPPDATA%\Programs\Python\Python312\Scripts\pywin32_postinstall.py" -install
    echo.
    pause
    exit /b 1
)

:: -- 6. Pos-install do pywin32 (necessario em alguns casos) ---
:: Algumas instalacoes do pywin32 precisam rodar o postinstall
:: para registrar as DLLs. Roda silenciosamente.
python -c "import win32api; win32api.GetCurrentProcessId()" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [INFO] Rodando post-install do pywin32...
    for /f "delims=" %%p in ('python -c "import sys, os; print(os.path.join(sys.prefix, 'Scripts', 'pywin32_postinstall.py'))"') do (
        if exist "%%p" python "%%p" -install >nul 2>&1
    )
)

echo  [OK] Dependencias instaladas e validadas.

:: Salva cache de sucesso
echo OK> "%DEPS_CACHE_FILE%"
exit /b 0
