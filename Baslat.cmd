@echo off
cd /d "%~dp0"
if exist "dist\DSF-Studio\DSF-Studio.exe" (
    start "" "dist\DSF-Studio\DSF-Studio.exe"
) else if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "main.py"
) else (
    echo Once README.md dosyasindaki kurulum adimlarini uygulayin.
    pause
)
