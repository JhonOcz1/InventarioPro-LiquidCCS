@echo off
title Sistema de Inventario Pro - LiquidCCS
cd /d "%~dp0"

echo ========================================================
echo INICIANDO APP DE INVENTARIO (DESK / MOBILE READY)
echo ========================================================
echo.

IF EXIST venv\Scripts\python.exe (
    venv\Scripts\python.exe main.py
) ELSE (
    python main.py
)

pause
