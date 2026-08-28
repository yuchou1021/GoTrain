@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 Python，请安装 Python 3.11+ 并勾选 "Add python.exe to PATH"
    pause
    exit /b 1
)
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo 依赖安装完成。请把 katago.exe 与权重文件放到 engine_bin 目录后运行 run.bat
pause
