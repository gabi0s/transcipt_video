@echo off
echo ==========================================
echo    SERVEUR DE TRANSCRIPTION AUDIO/VIDEO
echo ==========================================
echo.

REM Verification de Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERREUR: Python n'est pas installe ou pas dans le PATH
    echo Installez Python depuis https://python.org
    pause
    exit /b 1
)

REM Creation de l'environnement virtuel si necessaire
if not exist "venv" (
    echo Creation de l'environnement virtuel...
    python -m venv venv
    if errorlevel 1 (
        echo ERREUR: Impossible de creer l'environnement virtuel
        pause
        exit /b 1
    )
)

REM Activation de l'environnement virtuel
echo Activation de l'environnement virtuel...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERREUR: Impossible d'activer l'environnement virtuel
    pause
    exit /b 1
)

REM Installation des dependances
echo Installation des dependances...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERREUR: Impossible d'installer les dependances
    pause
    exit /b 1
)

REM Creation des dossiers necessaires
if not exist "templates" mkdir templates
if not exist "uploads" mkdir uploads
if not exist "sorties" mkdir sorties

REM Copie du fichier HTML dans templates si necessaire
if not exist "templates\index.html" (
    echo ATTENTION: Copiez votre fichier index.html dans le dossier templates/
    echo Le serveur va demarrer mais l'interface ne sera pas disponible
    echo.
)

REM Demarrage du serveur
echo.
echo ==========================================
echo    DEMARRAGE DU SERVEUR...
echo ==========================================
echo Interface web disponible sur: http://localhost:5000
echo Appuyez sur Ctrl+C pour arreter le serveur
echo.

python app.py

echo.
echo ==========================================
echo    SERVEUR ARRETE
echo ==========================================
pause