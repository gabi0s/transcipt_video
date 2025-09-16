#  Transcripteur Vidéo/Audio

## Description
Outil pour transcrire des vidéos et fichiers audio en texte, avec support des fichiers locaux et, si souhaité, de liens YouTube. Génère des transcriptions au format TXT et/ou SRT.
L’exécution est prévue sur CPU (pas de GPU requis) via faster-whisper en compute_type=int8.

## Fonctionnalités
*   **🎯 Support multiple** : Fichiers locaux (MP4, MKV, MOV, AVI, MP3, WAV, M4A, FLAC, WEBM)
*   **🧠 Modèles Whisper** : Plusieurs modèles de différentes tailles (tiny, base, small, medium, large-v3)
*   **🌍 Multilingue** : Détection automatique de langue ou sélection manuelle
*   **⚡ Options avancées** : Détection d'activité vocale (VAD), choix du format de sortie
*   **📊 Interface moderne** : Interface web intuitive avec glisser-déposer
*   **🔔 Notifications en temps réel** : Progression détaillée pendant la transcription

## Installation

## Windows (recommandé)

Double-cliquer sur run_server.bat.
Ce script :

1. crée/active un environnement virtuel venv,

2. installe les dépendances Python nécessaires (CPU),

3. vérifie la présence de FFmpeg dans le PATH,

4. lance l’application Flask.

## macOS / Linux
```bash
chmod +x install.sh
./install.sh
python app.py
```

### Prérequis
*   Python 3.8+
*   FFmpeg (à installer et à mettre /bin dans les variables d'environement) (https://www.ffmpeg.org/download.html)

### Dépendances
Si vous préférez passer par un fichier de dépendances :
```bash
pip install -r requirements.txt
```

## Lancer l'application
clicker sur le fichier .bat ```run_server.bat```
```bash
python app.py
```
Puis ouvrez votre navigateur à l'adresse : http://localhost:5000


## Structure du projet
```bash
transcripteur-app/
├── app.py                 # Application Flask principale
├── transcribe.py          # Logique de transcription
├── requirements.txt       # Dépendances Python
client
├── templates/
│   └── index.html        # Interface utilisateur
├── templates/
│   └── static.css        # Feuille de style
├── uploads/              # Fichiers uploadés (créé automatiquement)
└── transcriptions/       # Résultats de transcription (créé automatiquement)
```

## Modèles Whisper
Les modèles sont téléchargés automatiquement au premier usage et stockés dans le cache de votre système.

## Chemin de FFmpeg
Le chemin par défaut est configuré pour Windows. Pour d'autres systèmes, modifiez la variable ffmpeg_path dans transcribe.py.