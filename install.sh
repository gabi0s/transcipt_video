#!/usr/bin/env bash
set -e

echo "=== Installation transcript_video ==="

# Vérifier si Python est installé
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python n'est pas installé. Installe-le avant de continuer."
    exit 1
fi

echo "✅ Python détecté : $($PYTHON_CMD --version)"

# Créer un venv local
if [ ! -d "venv" ]; then
    echo "📦 Création d'un environnement virtuel (venv)..."
    $PYTHON_CMD -m venv venv
fi

# Activer le venv
echo "🔑 Activation de l'environnement virtuel..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Mise à jour de pip..."
pip install --upgrade pip

# Installer ffmpeg si non présent
if ! command -v ffmpeg &>/dev/null; then
    echo "⚠️  ffmpeg non trouvé. Installation..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install -y ffmpeg
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install ffmpeg
    elif [[ "$OSTYPE" == "msys" ]]; then
        echo "⚠️ Sous Windows, installe ffmpeg manuellement : https://ffmpeg.org/download.html"
    else
        echo "❌ OS non supporté automatiquement. Installe ffmpeg manuellement."
    fi
else
    echo "✅ ffmpeg déjà installé : $(ffmpeg -version | head -n1)"
fi


echo "=== Installation terminée ==="

