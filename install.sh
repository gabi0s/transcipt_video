#!/usr/bin/env bash
set -e

echo "=== Installation transcript_video ==="

# Détection Python
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python n'est pas installé. Installe-le avant de continuer."
    exit 1
fi
echo "✅ Python détecté : $($PYTHON_CMD --version)"

# Créer venv
if [ ! -d "venv" ]; then
    echo "📦 Création d'un environnement virtuel (venv)..."
    $PYTHON_CMD -m venv venv
fi

# Activer venv
echo "🔑 Activation de l'environnement virtuel..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
  # Git Bash sous Windows
  source venv/Scripts/activate
else
  source venv/bin/activate
fi

# Upgrade pip et outils de build
echo "⬆️  Mise à jour de pip/wheel/setuptools..."
pip install --upgrade pip wheel setuptools

# FFmpeg (si manquant)
if ! command -v ffmpeg &>/dev/null; then
    echo "⚠️  ffmpeg non trouvé. Installation..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install -y ffmpeg
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install ffmpeg
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        echo "⚠️  Sous Windows, installe ffmpeg manuellement : https://ffmpeg.org/download.html"
    else
        echo "❌ OS non supporté automatiquement. Installe ffmpeg manuellement."
    fi
else
    echo "✅ ffmpeg déjà installé : $(ffmpeg -version | head -n1)"
fi

# Dépendances Python (CPU)
echo "📦 Installation des dépendances Python..."
pip install faster-whisper ffmpeg-python yt-dlp tqdm flask

echo "=== Installation terminée ==="
