@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale em https://www.python.org/downloads/ ^(marque "Add to PATH"^)
  echo ou baixe o FairScan.exe na pagina de Releases do projeto.
  pause
  exit /b 3
)
python -m fairscan %*
echo.
pause
