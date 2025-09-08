#  Transcripteur Vidéo/Audio

## Description
Un outil puissant pour transcrire des vidéos et fichiers audio en texte, avec support des fichiers locaux et des URLs YouTube. Génère des transcriptions en format TXT et/ou SRT.

## Fonctionnalités
*   **🎯 Support multiple** : Fichiers locaux (MP4, MKV, MOV, AVI, MP3, WAV, M4A, FLAC, WEBM) et URLs YouTube
*   **🧠 Modèles Whisper** : Plusieurs modèles de différentes tailles (tiny, base, small, medium, large-v3)
*   **🌍 Multilingue** : Détection automatique de langue ou sélection manuelle
*   **⚡ Options avancées** : Détection d'activité vocale (VAD), choix du format de sortie
*   **📊 Interface moderne** : Interface web intuitive avec glisser-déposer
*   **🔔 Notifications en temps réel** : Progression détaillée pendant la transcription

## Installation

### Prérequis
*   Python 3.8+
*   FFmpeg (inclus dans le projet pour Windows)

### Dépendances
```bash
pip install -r requirements.txt
```

## Lancer l'application
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
├── uploads/              # Fichiers uploadés (créé automatiquement)
└── transcriptions/       # Résultats de transcription (créé automatiquement)
```

## Modèles Whisper
Les modèles sont téléchargés automatiquement au premier usage et stockés dans le cache de votre système.

## Chemin de FFmpeg
Le chemin par défaut est configuré pour Windows. Pour d'autres systèmes, modifiez la variable ffmpeg_path dans transcribe.py.