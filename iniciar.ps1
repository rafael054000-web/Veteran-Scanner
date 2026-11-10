# Veteran Scanner - execucao temporaria (nada fica instalado)
#
# Uso: abra o PowerShell como administrador e cole:
#   irm https://raw.githubusercontent.com/rafael054000-web/Veteran-Scanner/main/iniciar.ps1 | iex
#
# O que este script faz:
#   1. Baixa o VeteranScanner.exe oficial da release "latest" para uma pasta temporaria
#   2. Confere o SHA256 com o SHA256SUMS.txt publicado junto
#   3. Abre o scanner (o relatorio vai para a Area de Trabalho)
#   4. Apaga a pasta temporaria no final

& {
    $ErrorActionPreference = "Stop"
    $ProgressPreference = "SilentlyContinue"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

    $repo    = "rafael054000-web/Veteran-Scanner"
    $base    = "https://github.com/$repo/releases/latest/download"
    $work    = Join-Path $env:TEMP ("veteran_" + [guid]::NewGuid().ToString("N").Substring(0, 8))
    $exe     = Join-Path $work "VeteranScanner.exe"
    $sums    = Join-Path $work "SHA256SUMS.txt"
    $desktop = [Environment]::GetFolderPath("Desktop")

    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $isAdmin  = ([Security.Principal.WindowsPrincipal]$identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Host "Aviso: o PowerShell nao esta como administrador. A verificacao sera menos completa." -ForegroundColor Yellow
        Write-Host "Para a verificacao completa, feche e abra o PowerShell com 'Executar como administrador'." -ForegroundColor Yellow
        Write-Host ""
    }

    New-Item -ItemType Directory -Path $work -Force | Out-Null
    try {
        Write-Host "Baixando o Veteran Scanner oficial..." -ForegroundColor Cyan
        Invoke-WebRequest "$base/SHA256SUMS.txt" -OutFile $sums -UseBasicParsing
        Invoke-WebRequest "$base/VeteranScanner.exe" -OutFile $exe -UseBasicParsing

        $expected = ((Get-Content $sums -Raw).Trim() -split '\s+')[0].ToLower()
        $actual   = (Get-FileHash $exe -Algorithm SHA256).Hash.ToLower()
        if ($expected -ne $actual) {
            throw "O SHA256 do arquivo baixado nao confere. Por seguranca, o scanner nao sera aberto."
        }
        Write-Host "SHA256 conferido: $actual" -ForegroundColor Green
        Write-Host ""

        & $exe --output $desktop
    }
    catch {
        Write-Host "Erro: $($_.Exception.Message)" -ForegroundColor Red
    }
    finally {
        Start-Sleep -Milliseconds 500
        Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "Arquivos temporarios do scanner removidos. O relatorio (se salvo) esta na Area de Trabalho."
    }
}
