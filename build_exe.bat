@echo off
chcp 65001 >nul
cd /d "%~dp0"
call .venv\Scripts\activate.bat
pip install pyinstaller
pyinstaller --noconfirm --windowed --name "围棋训练助手" main.py
if exist "dist\围棋训练助手\engine_bin" rd /s /q "dist\围棋训练助手\engine_bin"
xcopy /e /i /y engine_bin "dist\围棋训练助手\engine_bin"
if exist "dist\围棋训练助手\config" rd /s /q "dist\围棋训练助手\config"
xcopy /e /i /y config "dist\围棋训练助手\config"
echo.
echo 打包完成：dist\围棋训练助手\围棋训练助手.exe
pause
