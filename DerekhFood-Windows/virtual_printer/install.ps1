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
    Write-Host "  [AVISO] Impressora '$PrinterName' ja esta instalada." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Detalhes da impressora atual:" -ForegroundColor White
    Write-Host "    Nome:   $($existing.Name)" -ForegroundColor Gray
    Write-Host "    Driver: $($existing.DriverName)" -ForegroundColor Gray
    Write-Host "    Porta:  $($existing.PortName)" -ForegroundColor Gray
    Write-Host "    Status: $($existing.PrinterStatus)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  O que voce quer fazer?" -ForegroundColor Cyan
    Write-Host "    [M] Manter a impressora atual (recomendado)" -ForegroundColor White
    Write-Host "    [R] Reinstalar (remove e cria novamente)" -ForegroundColor White
    Write-Host ""

    do {
        $escolha = Read-Host "  Digite M ou R"
        $escolha = $escolha.ToUpper().Trim()
    } while ($escolha -ne "M" -and $escolha -ne "R")

    if ($escolha -eq "M") {
        Write-Host ""
        Write-Host "  [OK] Mantendo impressora atual. Nada foi alterado." -ForegroundColor Green
        Write-Host ""
        exit 0
    }

    # Reinstalar: remover impressora + porta existente
    Write-Host ""
    Write-Host "  Removendo impressora atual..." -NoNewline
    try {
        Remove-Printer -Name $PrinterName -ErrorAction Stop
        Write-Host " OK" -ForegroundColor Green
    } catch {
        Write-Host " ERRO: $_" -ForegroundColor Red
        exit 1
    }

    # Remover porta antiga (se existir e nao for usada por outras impressoras)
    $oldPort = Get-PrinterPort -Name $PortName -ErrorAction SilentlyContinue
    if ($oldPort) {
        Write-Host "  Removendo porta antiga '$PortName'..." -NoNewline
        try {
            Remove-PrinterPort -Name $PortName -ErrorAction Stop
            Write-Host " OK" -ForegroundColor Green
        } catch {
            Write-Host " (em uso, continuando)" -ForegroundColor Yellow
        }
    }
    Write-Host ""
    Write-Host "  Prosseguindo com reinstalacao..." -ForegroundColor Cyan
    Write-Host ""
}

# ── 2. Verificar/instalar driver ─────────────────────────────────────────────

Write-Host "  [1/4] Verificando driver '$DriverName'..." -NoNewline
$driver = Get-PrinterDriver -Name $DriverName -ErrorAction SilentlyContinue

if (-not $driver) {
    Write-Host " (nao instalado)" -ForegroundColor Yellow
    Write-Host "         Tentando instalar driver nativo..." -NoNewline
    try {
        Add-PrinterDriver -Name $DriverName -ErrorAction Stop
        Write-Host " OK" -ForegroundColor Green
        $driver = Get-PrinterDriver -Name $DriverName -ErrorAction SilentlyContinue
    } catch {
        Write-Host " FALHA" -ForegroundColor Red
        Write-Host "         Erro: $_" -ForegroundColor DarkRed

        # Fallback: tentar via pnputil com INF do Windows
        Write-Host "         Tentando via pnputil (INF nativo)..." -NoNewline
        $infFiles = @(
            "$env:WINDIR\inf\prnms001.inf",
            "$env:WINDIR\inf\ntprint.inf"
        )
        $pnpOk = $false
        foreach ($inf in $infFiles) {
            if (Test-Path $inf) {
                try {
                    pnputil /add-driver $inf /install 2>&1 | Out-Null
                    Start-Sleep -Seconds 2
                    Add-PrinterDriver -Name $DriverName -ErrorAction Stop
                    $pnpOk = $true
                    break
                } catch { }
            }
        }
        if ($pnpOk) {
            Write-Host " OK" -ForegroundColor Green
            $driver = Get-PrinterDriver -Name $DriverName -ErrorAction SilentlyContinue
        } else {
            Write-Host " FALHA" -ForegroundColor Red
        }
    }
}

if (-not $driver) {
    Write-Host ""
    Write-Host "  ERRO: Driver '$DriverName' nao esta disponivel neste Windows." -ForegroundColor Red
    Write-Host ""
    Write-Host "  Drivers disponiveis no seu sistema:" -ForegroundColor Yellow
    Get-PrinterDriver | Select-Object -First 20 | ForEach-Object {
        Write-Host "    - $($_.Name)" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "  SOLUCAO:" -ForegroundColor Cyan
    Write-Host "    1. Abra 'Configuracoes' > 'Bluetooth e dispositivos' > 'Impressoras'" -ForegroundColor White
    Write-Host "    2. Clique 'Adicionar dispositivo' > 'Adicionar manualmente'" -ForegroundColor White
    Write-Host "    3. Escolha 'Adicionar impressora local'" -ForegroundColor White
    Write-Host "    4. Criar porta TCP/IP 127.0.0.1:9100" -ForegroundColor White
    Write-Host "    5. Na selecao de driver, escolha 'Generico' > 'Generic / Text Only'" -ForegroundColor White
    Write-Host ""
    exit 1
}
Write-Host "         Driver OK." -ForegroundColor Green

# ── 3. Criar porta TCP/IP ───────────────────────────────────────────────────

Write-Host "  [2/4] Criando porta TCP/IP '$PortName'..." -NoNewline

$existingPort = Get-PrinterPort -Name $PortName -ErrorAction SilentlyContinue
if ($existingPort) {
    Write-Host " (ja existe)" -ForegroundColor Yellow
} else {
    $portCriada = $false
    try {
        # Criar porta TCP/IP RAW (porta 9100)
        # -SNMP removido: causa HRESULT 0x80070057 em algumas versoes do Win
        # SNMP sera desabilitado via registry apos criacao
        Add-PrinterPort -Name $PortName `
            -PrinterHostAddress $PortIP `
            -PortNumber $PortNumber `
            -ErrorAction Stop
        Write-Host " OK" -ForegroundColor Green
        $portCriada = $true
    } catch {
        Write-Host " (tentando WMI)" -ForegroundColor Yellow
        try {
            $wmi = ([wmiclass]"Win32_TcpIpPrinterPort").CreateInstance()
            $wmi.Name = $PortName
            $wmi.Protocol = 1  # RAW
            $wmi.HostAddress = $PortIP
            $wmi.PortNumber = $PortNumber
            $wmi.SNMPEnabled = $false
            $wmi.Put() | Out-Null
            Write-Host "         OK (via WMI)" -ForegroundColor Green
            $portCriada = $true
        } catch {
            Write-Host "         ERRO" -ForegroundColor Red
            Write-Host "         Falha ao criar porta: $_" -ForegroundColor Red
            exit 1
        }
    }

    # Desabilitar SNMP via registry (evita status "offline" quando servidor nao responde)
    if ($portCriada) {
        try {
            $regPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Print\Monitors\Standard TCP/IP Port\Ports\$PortName"
            if (Test-Path $regPath) {
                Set-ItemProperty -Path $regPath -Name "SNMP Enabled" -Value 0 -Type DWord -ErrorAction SilentlyContinue
                Set-ItemProperty -Path $regPath -Name "Protocol" -Value 1 -Type DWord -ErrorAction SilentlyContinue
            }
        } catch { }
    }
}

# ── 4. Criar impressora ─────────────────────────────────────────────────────

Write-Host "  [3/4] Criando impressora '$PrinterName'..." -NoNewline
try {
    # -Shared removido: default ja e nao-compartilhado
    # -Shared $false gera erro "positional parameter cannot be found"
    Add-Printer -Name $PrinterName `
        -DriverName $DriverName `
        -PortName $PortName `
        -Comment "Impressora termica virtual para testes Derekh Food" `
        -ErrorAction Stop
    Write-Host " OK" -ForegroundColor Green
} catch {
    Write-Host " ERRO" -ForegroundColor Red
    Write-Host "  Falha ao criar impressora: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Verifique em 'Get-PrinterDriver' se o driver esta instalado." -ForegroundColor Yellow
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
