#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Instala a impressora virtual "Termica Virtual 80mm" no Windows.

.DESCRIPTION
    Cria uma porta TCP/IP apontando para 127.0.0.1:9100 (protocolo RAW/JetDirect)
    e instala uma impressora usando o driver "Generic / Text Only" (nativo Windows).
    O driver envia bytes brutos sem processamento — identico a uma termica real.

.NOTES
    - Requer privilegios de Administrador
    - SNMP desabilitado para evitar status "offline" quando o servidor TCP nao responde
    - A porta 9100 e padrao JetDirect — exatamente como impressoras termicas reais

.EXAMPLE
    # Em PowerShell elevado (Admin):
    .\install.ps1
#>

$PrinterName = "Termica Virtual 80mm"
$PortName = "VPORT_TERMICA_9100"
$PortIP = "127.0.0.1"
$PortNumber = 9100
$DriverName = "Generic / Text Only"

Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "  Instalando Impressora Termica Virtual" -ForegroundColor Cyan
Write-Host "  $PrinterName" -ForegroundColor Yellow
Write-Host "  TCP/IP $PortIP`:$PortNumber" -ForegroundColor Yellow
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Verificar se ja existe ────────────────────────────────────────────────

$existing = Get-Printer -Name $PrinterName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "  [OK] Impressora '$PrinterName' ja existe." -ForegroundColor Green
    Write-Host "  Para reinstalar, execute uninstall.ps1 primeiro." -ForegroundColor Yellow
    Write-Host ""
    exit 0
}

# ── 2. Verificar driver disponivel ───────────────────────────────────────────

Write-Host "  [1/4] Verificando driver '$DriverName'..." -NoNewline
$driver = Get-PrinterDriver -Name $DriverName -ErrorAction SilentlyContinue
if (-not $driver) {
    Write-Host " ERRO" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Driver '$DriverName' nao encontrado!" -ForegroundColor Red
    Write-Host "  Este driver deveria estar instalado por padrao no Windows." -ForegroundColor Red
    Write-Host "  Tente: Painel de Controle > Programas > Ativar recursos do Windows" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}
Write-Host " OK" -ForegroundColor Green

# ── 3. Criar porta TCP/IP ───────────────────────────────────────────────────

Write-Host "  [2/4] Criando porta TCP/IP '$PortName'..." -NoNewline

$existingPort = Get-PrinterPort -Name $PortName -ErrorAction SilentlyContinue
if ($existingPort) {
    Write-Host " (ja existe)" -ForegroundColor Yellow
} else {
    try {
        # Criar porta TCP/IP RAW (porta 9100, SNMP desabilitado)
        Add-PrinterPort -Name $PortName `
            -PrinterHostAddress $PortIP `
            -PortNumber $PortNumber `
            -SNMP 0
        Write-Host " OK" -ForegroundColor Green
    } catch {
        Write-Host " ERRO" -ForegroundColor Red
        Write-Host "  Falha ao criar porta: $_" -ForegroundColor Red

        # Tentativa alternativa via WMI
        Write-Host "  Tentando via WMI..." -NoNewline
        try {
            $wmi = ([wmiclass]"Win32_TcpIpPrinterPort").CreateInstance()
            $wmi.Name = $PortName
            $wmi.Protocol = 1  # RAW
            $wmi.HostAddress = $PortIP
            $wmi.PortNumber = $PortNumber
            $wmi.SNMPEnabled = $false
            $wmi.Put() | Out-Null
            Write-Host " OK (WMI)" -ForegroundColor Green
        } catch {
            Write-Host " ERRO" -ForegroundColor Red
            Write-Host "  Nao foi possivel criar a porta TCP/IP." -ForegroundColor Red
            Write-Host "  Tente criar manualmente: Configuracoes > Impressoras > Adicionar porta TCP/IP" -ForegroundColor Yellow
            exit 1
        }
    }
}

# ── 4. Criar impressora ─────────────────────────────────────────────────────

Write-Host "  [3/4] Criando impressora '$PrinterName'..." -NoNewline
try {
    Add-Printer -Name $PrinterName `
        -DriverName $DriverName `
        -PortName $PortName `
        -Comment "Impressora termica virtual para testes Derekh Food" `
        -Shared $false
    Write-Host " OK" -ForegroundColor Green
} catch {
    Write-Host " ERRO" -ForegroundColor Red
    Write-Host "  Falha ao criar impressora: $_" -ForegroundColor Red
    exit 1
}

# ── 5. Verificar instalacao ──────────────────────────────────────────────────

Write-Host "  [4/4] Verificando instalacao..." -NoNewline
$printer = Get-Printer -Name $PrinterName -ErrorAction SilentlyContinue
if ($printer) {
    Write-Host " OK" -ForegroundColor Green
    Write-Host ""
    Write-Host "  =================================================" -ForegroundColor Green
    Write-Host "  Impressora instalada com sucesso!" -ForegroundColor Green
    Write-Host "  =================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Nome:     $PrinterName" -ForegroundColor White
    Write-Host "  Driver:   $DriverName" -ForegroundColor White
    Write-Host "  Porta:    $PortName ($PortIP`:$PortNumber)" -ForegroundColor White
    Write-Host "  Status:   $($printer.PrinterStatus)" -ForegroundColor White
    Write-Host ""
    Write-Host "  Proximo passo:" -ForegroundColor Yellow
    Write-Host "    1. Inicie o servidor: python -m virtual_printer server" -ForegroundColor Yellow
    Write-Host "    2. Teste: python -m virtual_printer simulate" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host " FALHA" -ForegroundColor Red
    Write-Host "  A impressora nao foi encontrada apos criacao." -ForegroundColor Red
    exit 1
}
