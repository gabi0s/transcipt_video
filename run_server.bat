@echo off
setlocal EnableExtensions

echo ===============================================
echo   Transcripteur - Installation et Lancement
echo ===============================================

REM 1) Détection de Python
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  set "PY=python"
) else (
  where python3 >nul 2>nul
  if %ERRORLEVEL% EQU 0 (
    set "PY=python3"
  ) else (
    echo [ERREUR] Python non trouve. Installe Python puis relance ce script.
    exit /b 1
  )
)

REM 2) Création/activation du venv
if not exist "venv" (
  echo [INFO] Creation de l'environnement virtuel...
  %PY% -m venv venv
)
call "venv\Scripts\activate.bat"

REM 3) Installation des dependances
echo [INFO] Mise a jour de pip / wheel / setuptools...
python -m pip install --upgrade pip wheel setuptools

echo [INFO] Installation des dependances Python...
REM plus leger et suffisant pour CPU
python -m pip install faster-whisper ffmpeg-python yt-dlp tqdm flask

REM 4) Verification FFmpeg (optionnel mais recommande)
where ffmpeg >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
  echo [ATTENTION] FFmpeg n'est pas dans le PATH. Installe-le ou ajoute-le au PATH.
  echo            Telechargement: https://ffmpeg.org/download.html
)

echo.
echo ===============================================
echo   Lancement du serveur (Flask)
echo   URL: http://localhost:5000
echo ===============================================
python app.py

endlocal
