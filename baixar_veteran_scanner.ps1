# Baixa (ou atualiza) o VeteranScanner.exe oficial da release "latest" do GitHub e confere o SHA256.
# Usado pelo executar.bat. Não precisa de Python.

param([string]$Repo = "rafael054000-web/Veteran-Scanner")

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$dir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe  = Join-Path $dir "VeteranScanner.exe"
$sums = Join-Path $env:TEMP "veteran_SHA256SUMS.txt"
$tmp  = Join-Path $env:TEMP "VeteranScanner_download.exe"
$base = "https://github.com/$Repo/releases/latest/download"

Invoke-WebRequest "$base/SHA256SUMS.txt" -OutFile $sums -UseBasicParsing
$expected = ((Get-Content $sums -Raw).Trim() -split '\s+')[0].ToLower()
if ($expected -notmatch '^[0-9a-f]{64}$') { throw "SHA256SUMS.txt inválido" }

if (Test-Path $exe) {
    $current = (Get-FileHash $exe -Algorithm SHA256).Hash.ToLower()
    if ($current -eq $expected) {
        Write-Host "VeteranScanner.exe já está na versão mais recente."
        exit 0
    }
    Write-Host "Atualizando o VeteranScanner.exe..."
} else {
    Write-Host "Baixando o VeteranScanner.exe oficial do GitHub..."
}

Invoke-WebRequest "$base/VeteranScanner.exe" -OutFile $tmp -UseBasicParsing
$actual = (Get-FileHash $tmp -Algorithm SHA256).Hash.ToLower()
if ($actual -ne $expected) {
    Remove-Item $tmp -Force
    throw "O SHA256 do arquivo baixado não confere. Download cancelado."
}
Move-Item $tmp $exe -Force
Write-Host "SHA256 conferido: $actual"
