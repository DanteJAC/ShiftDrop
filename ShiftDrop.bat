@echo off
title ShiftDrop - Conversor Radial para Windows
cd /d "%~dp0"
echo ============================================================
echo   ⚡ ShiftDrop - Conversor Multimedia y Documentos 100%% Local
echo ============================================================
echo   - Arrastra archivos mientras mantienes presionada la tecla Shift.
echo   - Aparecera la rueda con opciones contextuales instantaneas.
echo   - Minimizado en la bandeja del sistema (System Tray).
echo ============================================================

if exist "dist\ShiftDrop.exe" (
    echo Iniciando ejecutable independiente ShiftDrop.exe...
    start "" "dist\ShiftDrop.exe"
    echo ShiftDrop esta corriendo en segundo plano y en la bandeja del sistema.
    exit /b 0
)

echo Iniciando entorno y servicios de escucha con Python...
uv run python -m shiftdrop.main
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] La aplicacion se cerro con codigo de salida %ERRORLEVEL%.
    pause
)
