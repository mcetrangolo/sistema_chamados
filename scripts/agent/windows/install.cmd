@echo off
setlocal

net session >nul 2>&1
if %errorlevel% neq 0 (
  echo Solicitando permissao de Administrador...
  powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)

powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0install.ps1"
echo.
pause
