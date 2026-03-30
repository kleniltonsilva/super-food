#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Remove a impressora virtual "Termica Virtual 80mm" do Windows.

.DESCRIPTION
    Remove a impressora e a porta TCP/IP associada.

.EXAMPLE
    # Em PowerShell elevado (Admin):
    .\uninstall.ps1
#>

$PrinterName = "Termica Virtual 80mm"
$PortName = "VPORT_TERMICA_9100"

Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "  Removendo Impressora Termica Virtual" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Remover impressora ───────────────────────────────────────────────────

Write-Host "  [1/2] Removendo impressora '$PrinterName'..." -NoNewline
$printer = Get-Printer -Name $PrinterName -ErrorAction SilentlyContinue
if ($printer) {
    try {
        Remove-Printer -Name $PrinterName
        Write-Host " OK" -ForegroundColor Green
    } catch {
        Write-Host " ERRO" -ForegroundColor Red
        Write-Host "  $_" -ForegroundColor Red
    }
} else {
    Write-Host " (nao encontrada)" -ForegroundColor Yellow
}

# ── 2. Remover porta ────────────────────────────────────────────────────────

Write-Host "  [2/2] Removendo porta '$PortName'..." -NoNewline
$port = Get-PrinterPort -Name $PortName -ErrorAction SilentlyContinue
if ($port) {
    try {
        Remove-PrinterPort -Name $PortName
        Write-Host " OK" -ForegroundColor Green
    } catch {
        Write-Host " ERRO" -ForegroundColor Red
        Write-Host "  $_" -ForegroundColor Red
    }
} else {
    Write-Host " (nao encontrada)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Desinstalacao concluida." -ForegroundColor Green
Write-Host ""
