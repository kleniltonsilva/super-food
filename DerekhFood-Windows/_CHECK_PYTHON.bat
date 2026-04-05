@echo off
:: ============================================================
::  _CHECK_PYTHON.bat
::  Detecta Python 3.12 e instala automaticamente se ausente.
::
::  Uso (nos outros .bat):
::      call "%~dp0_CHECK_PYTHON.bat"
::      if %ERRORLEVEL% NEQ 0 exit /b 1
::
::  IMPORTANTE: Nao usa 'setlocal' porque precisa propagar o
::  PATH atualizado de volta ao script pai que o chama.
:: ============================================================

:: -- 1. Verifica se Python ja esta no PATH --------------------
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 goto :check_version

:: -- 2. Verifica se ja foi instalado mas nao esta no PATH -----
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    echo  [INFO] Python 3.12 encontrado em %LOCALAPPDATA%\Programs\Python\Python312
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
    python --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 goto :check_version
)

if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    echo  [INFO] Python 3.13 encontrado em %LOCALAPPDATA%\Programs\Python\Python313
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python313;%LOCALAPPDATA%\Programs\Python\Python313\Scripts;%PATH%"
    python --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 goto :check_version
)

:: -- 3. Instalar Python 3.12 automaticamente ------------------
echo.
echo  +--------------------------------------------------+
echo  ^|  Python 3.12 nao encontrado neste computador.   ^|
echo  ^|  Vou baixar e instalar automaticamente.         ^|
echo  ^|                                                  ^|
echo  ^|  Tempo estimado: 2-3 minutos (depende da net)   ^|
echo  ^|  NAO FECHE esta janela!                          ^|
echo  +--------------------------------------------------+
echo.

set "PY_VERSION=3.12.8"
set "PY_URL=https://www.python.org/ftp/python/%PY_VERSION%/python-%PY_VERSION%-amd64.exe"
set "PY_INSTALLER=%TEMP%\python-%PY_VERSION%-amd64.exe"

echo  [1/3] Baixando Python %PY_VERSION%...
echo         URL: %PY_URL%

:: Verifica se curl esta disponivel (Windows 10 1803+ tem nativo)
where curl >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    curl -L --fail --silent --show-error -o "%PY_INSTALLER%" "%PY_URL%"
) else (
    :: Fallback: PowerShell Invoke-WebRequest
    powershell -NoProfile -ExecutionPolicy Bypass -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_INSTALLER%' -UseBasicParsing } catch { exit 1 }"
)

if not exist "%PY_INSTALLER%" (
    echo.
    echo  [ERRO] Falha ao baixar Python. Verifique sua conexao de internet.
    echo         URL: %PY_URL%
    echo.
    echo  Alternativa manual:
    echo    1. Acesse: https://www.python.org/downloads/
    echo    2. Baixe Python 3.12 ou superior
    echo    3. MARQUE "Add Python to PATH" durante a instalacao
    echo    4. Rode este script novamente
    echo.
    pause
    exit /b 1
)

echo         Download concluido!
echo.
echo  [2/3] Instalando Python (isso pode levar 1-2 minutos)...
echo         Instalando em modo silencioso, apenas para o usuario atual.
echo         Nao precisa de permissao de Administrador.

:: /quiet           = instalacao silenciosa (sem UI)
:: InstallAllUsers=0 = instala apenas para o usuario atual (sem admin)
:: PrependPath=1    = adiciona Python ao PATH do usuario
:: Include_pip=1    = instala pip
:: Include_test=0   = nao instala suite de testes
:: Include_doc=0    = nao instala documentacao
:: Include_launcher=0 = nao instala py.exe launcher (evita conflitos)
"%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0 Include_doc=0 Include_launcher=0
set "INSTALL_RESULT=%ERRORLEVEL%"

:: Remove installer temporario
del "%PY_INSTALLER%" >nul 2>&1

if %INSTALL_RESULT% NEQ 0 (
    echo.
    echo  [ERRO] Instalacao do Python falhou (codigo %INSTALL_RESULT%).
    echo.
    echo  Alternativa manual:
    echo    1. Acesse: https://www.python.org/downloads/
    echo    2. Baixe Python 3.12 ou superior
    echo    3. MARQUE "Add Python to PATH" durante a instalacao
    echo    4. Rode este script novamente
    echo.
    pause
    exit /b 1
)

echo         Instalacao concluida!
echo.
echo  [3/3] Configurando PATH da sessao atual...

:: Adiciona ao PATH da sessao atual (setx eh persistente mas nao afeta processo atual)
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"

:: Valida
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [AVISO] Python foi instalado, mas ainda nao esta visivel nesta janela.
    echo.
    echo  SOLUCAO: Feche TODAS as janelas de cmd/PowerShell e abra de novo.
    echo           Depois rode este .bat novamente.
    echo.
    pause
    exit /b 1
)

:check_version
:: Exibe versao final
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "DETECTED_PY=%%i"
echo  [OK] Python %DETECTED_PY% pronto para uso.
exit /b 0
