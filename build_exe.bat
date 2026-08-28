@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
pip install pyinstaller
pyinstaller --noconfirm --windowed --name "GoTrainer" main.py
if exist "dist\GoTrainer\engine_bin" rd /s /q "dist\GoTrainer\engine_bin"
xcopy /e /i /y engine_bin "dist\GoTrainer\engine_bin"
if exist "dist\GoTrainer\config" rd /s /q "dist\GoTrainer\config"
xcopy /e /i /y config "dist\GoTrainer\config"
echo.
echo Build done: dist\GoTrainer\GoTrainer.exe
pause
