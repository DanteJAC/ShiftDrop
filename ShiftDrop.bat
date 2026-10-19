@echo off
title ShiftDrop
cd /d "%~dp0"
echo Iniciando ShiftDrop...
uv run python -m shiftdrop.main
pause
