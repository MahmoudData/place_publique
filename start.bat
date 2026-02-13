@echo off
setlocal

echo === Place Publique - Demarrage ===
echo.

set VENV=.venv\Scripts\python.exe
set APP_DIR=app

REM Verifier que le venv existe
if not exist "%VENV%" (
    echo ERREUR : venv introuvable (%VENV%)
    echo Creez-le avec : python -m venv .venv
    echo Puis installez les dependances : .venv\Scripts\pip install -r app\requirements.txt
    pause
    exit /b 1
)

echo [1/2] Demarrage du service d'inference...
start "Inference Service" cmd /k "cd /d %~dp0%APP_DIR% && %~dp0%VENV% inference_service.py"

timeout /t 3 /nobreak >nul

echo [2/2] Demarrage du serveur Flask...
start "Flask App" cmd /k "cd /d %~dp0%APP_DIR% && %~dp0%VENV% app.py"

echo.
echo Services demarres !
echo   - Service d'inference : fenetre "Inference Service"
echo   - Dashboard Flask     : fenetre "Flask App"
echo.
echo Dashboard disponible sur : http://localhost:5000
echo.
echo Fermez les fenetres pour arreter les services.
pause
