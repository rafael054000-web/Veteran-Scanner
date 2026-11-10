@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

rem Garante o VeteranScanner.exe oficial e atualizado (baixa da release "latest" e confere o SHA256).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0baixar_veteran_scanner.ps1"
if errorlevel 1 (
  echo.
  echo Nao foi possivel baixar ou atualizar o VeteranScanner.exe ^(sem internet?^).
  if exist "%~dp0VeteranScanner.exe" (
    echo Usando a copia que ja esta nesta pasta.
  ) else (
    where python >nul 2>nul
    if not errorlevel 1 (
      echo Usando o Python instalado.
      python -m veteran_scanner %*
      echo.
      pause
      exit /b
    )
    echo Baixe manualmente em: https://github.com/rafael054000-web/Veteran-Scanner/releases/latest
    pause
    exit /b 3
  )
)

"%~dp0VeteranScanner.exe" %*
