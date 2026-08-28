@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境，请先运行 setup.bat
    pause
    exit /b 1
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 pause
