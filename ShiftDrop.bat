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
echo Iniciando entorno y servicios de escucha...
uv run python -m shiftdrop.main
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] La aplicacion se cerro con codigo de salida %ERRORLEVEL%.
    pause
)
