import os
import re
import sys
import time
import threading
import tempfile
import ffmpeg
from pathlib import Path
from faster_whisper import WhisperModel
from tqdm import tqdm
from yt_dlp import YoutubeDL

class ProgressTracker:
    """Classe pour gérer les barres de progression et animations"""
    
    def __init__(self):
        self.stop_animation = False
        self.animation_thread = None
    
    def start_spinner(self, message: str):
        """Démarre une animation de chargement"""
        self.stop_animation = False
        self.animation_thread = threading.Thread(target=self._animate_spinner, args=(message,))
        self.animation_thread.daemon = True
        self.animation_thread.start()
    
    def stop_spinner(self):
        """Arrête l'animation de chargement"""
        self.stop_animation = True
        if self.animation_thread:
            self.animation_thread.join()
        print()  # Nouvelle ligne après l'animation
    
    def _animate_spinner(self, message: str):
        """Animation spinner tournante"""
        spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        idx = 0
        while not self.stop_animation:
            print(f'\r{spinner[idx]} {message}', end='', flush=True)
            idx = (idx + 1) % len(spinner)
            time.sleep(0.1)

class ProgressHook:
    """Hook personnalisé pour yt-dlp avec barre de progression"""
    
    def __init__(self):
        self.pbar = None
    
    def __call__(self, d):
        if d['status'] == 'downloading':
            if self.pbar is None:
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                self.pbar = tqdm(
                    total=total,
                    unit='B',
                    unit_scale=True,
                    desc="📥 Téléchargement",
                    bar_format='{desc}: {percentage:3.1f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
                )
            
            downloaded = d.get('downloaded_bytes', 0)
            if self.pbar.total and downloaded:
                self.pbar.n = downloaded
                self.pbar.refresh()
                
        elif d['status'] == 'finished':
            if self.pbar:
                self.pbar.close()
                print("✅ Téléchargement terminé")

class VideoTranscriber:
    def __init__(self):
        # Utilise le même chemin que votre code fonctionnel
        self.ffmpeg_path = "C:/AllProjects/transcipt_video/ffmpeg-master-latest-win64-gpl-shared/ffmpeg-master-latest-win64-gpl-shared/bin/ffmpeg.exe"
        self.supported_formats = ['.mp4', '.mkv', '.mov', '.avi', '.mp3', '.wav', '.m4a', '.flac', '.webm']
        self.whisper_models = {
            'tiny': 'Très rapide, précision basique (39 MB)',
            'base': 'Rapide, précision correcte (74 MB)', 
            'small': 'Équilibré vitesse/précision (244 MB)',
            'medium': 'Lent, bonne précision (769 MB)',
            'large-v3': 'Très lent, meilleure précision (1550 MB)'
        }
        self.progress_tracker = ProgressTracker()

    def is_url(self, s: str) -> bool:
        """Vérifie si l'entrée est une URL valide"""
        return s.startswith("http://") or s.startswith("https://")

    def display_header(self):
        """Affiche l'en-tête du programme"""
        print("=" * 60)
        print("🎥 TRANSCRIPTEUR VIDÉO/AUDIO AVANCÉ")
        print("   Conversion vidéo → texte avec suivi en temps réel")
        print("=" * 60)
        print()

    def get_source_choice(self) -> str:
        """Menu pour choisir la source (fichier local ou YouTube)"""
        print("📂 SÉLECTION DE LA SOURCE")
        print("-" * 30)
        print("1️⃣  Fichier local (vidéo/audio sur votre ordinateur)")
        print("2️⃣  URL YouTube (téléchargement automatique)")
        print()
        
        while True:
            choice = input("🔽 Votre choix (1 ou 2) : ").strip()
            if choice in ['1', '2']:
                return choice
            print("❌ Veuillez saisir 1 ou 2")

    def get_local_file(self) -> str:
        """Saisie et validation du fichier local"""
        print("\n📁 FICHIER LOCAL")
        print("-" * 20)
        print(f"Formats supportés : {', '.join(self.supported_formats)}")
        print()
        
        while True:
            file_path = input("📎 Chemin complet du fichier : ").strip().strip('"')
            
            if not file_path:
                print("❌ Veuillez saisir un chemin de fichier")
                continue
                
            # Vérification avec spinner
            self.progress_tracker.start_spinner("Vérification du fichier...")
            time.sleep(0.5)  # Simulation vérification
            
            if not os.path.exists(file_path):
                self.progress_tracker.stop_spinner()
                print(f"❌ Fichier introuvable : {file_path}")
                print("💡 Vérifiez le chemin et réessayez")
                continue
                
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in self.supported_formats:
                self.progress_tracker.stop_spinner()
                print(f"❌ Format non supporté : {file_ext}")
                print(f"💡 Formats acceptés : {', '.join(self.supported_formats)}")
                continue
            
            # Affichage info fichier
            file_size = os.path.getsize(file_path)
            size_mb = file_size / (1024 * 1024)
            self.progress_tracker.stop_spinner()
            print(f"✅ Fichier valide : {Path(file_path).name} ({size_mb:.1f} MB)")
            return file_path

    def get_youtube_url(self) -> str:
        """Saisie et validation de l'URL YouTube"""
        print("\n🌐 URL YOUTUBE")
        print("-" * 15)
        print("💡 Formats acceptés : youtube.com, youtu.be, etc.")
        print()
        
        while True:
            url = input("🔗 Collez l'URL YouTube : ").strip()
            
            if not url:
                print("❌ Veuillez saisir une URL")
                continue
                
            if not self.is_url(url):
                print("❌ URL invalide (doit commencer par http:// ou https://)")
                continue
            
            # Vérification de l'URL avec spinner
            self.progress_tracker.start_spinner("Vérification de l'URL...")
            
            try:
                # Test rapide de l'URL
                with YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'Titre non disponible')
                    duration = info.get('duration', 0)
                    
                self.progress_tracker.stop_spinner()
                print(f"✅ Vidéo trouvée : {title}")
                if duration:
                    minutes, seconds = divmod(duration, 60)
                    print(f"   ⏱️  Durée : {minutes:02d}:{seconds:02d}")
                return url
                
            except Exception as e:
                self.progress_tracker.stop_spinner()
                print(f"❌ Erreur URL : {e}")
                continue

    def get_model_choice(self) -> str:
        """Menu pour choisir le modèle Whisper"""
        print("\n🧠 MODÈLE DE TRANSCRIPTION")
        print("-" * 30)
        print("Choisissez selon vos besoins vitesse/précision :")
        print()
        
        for i, (model, desc) in enumerate(self.whisper_models.items(), 1):
            print(f"{i}️⃣  {model.ljust(10)} - {desc}")
        
        print("6️⃣  Défaut recommandé (small)")
        print()
        
        while True:
            choice = input("🔽 Votre choix (1-6) : ").strip()
            
            if choice == '6' or choice == '':
                return 'small'
            
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= 5:
                    return list(self.whisper_models.keys())[choice_num - 1]
                else:
                    print("❌ Veuillez choisir entre 1 et 6")
            except ValueError:
                print("❌ Veuillez saisir un numéro")

    def get_language_choice(self) -> str:
        """Menu pour choisir la langue"""
        print("\n🌍 LANGUE DE TRANSCRIPTION")
        print("-" * 25)
        
        common_langs = {
            'fr': 'Français',
            'en': 'Anglais', 
            'es': 'Espagnol',
            'de': 'Allemand',
            'it': 'Italien',
            'pt': 'Portugais',
            'auto': 'Détection automatique (recommandé)'
        }
        
        print("Langues courantes :")
        for i, (code, name) in enumerate(common_langs.items(), 1):
            print(f"{i}️⃣  {name} ({code})")
        
        print(f"{len(common_langs) + 1}️⃣  Autre langue (code ISO)")
        print()
        
        while True:
            choice = input("🔽 Votre choix : ").strip()
            
            if not choice or choice == '7':
                return None  # Auto-détection
                
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(common_langs):
                    lang_code = list(common_langs.keys())[choice_num - 1]
                    return None if lang_code == 'auto' else lang_code
                elif choice_num == len(common_langs) + 1:
                    custom_lang = input("Code langue ISO (ex: ja, zh, ru) : ").strip().lower()
                    return custom_lang if custom_lang else None
                else:
                    print(f"❌ Veuillez choisir entre 1 et {len(common_langs) + 1}")
            except ValueError:
                if len(choice) == 2 and choice.isalpha():
                    return choice.lower()
                print("❌ Veuillez saisir un numéro ou un code langue")

    def get_advanced_options(self) -> dict:
        """Menu pour les options avancées"""
        print("\n⚙️  OPTIONS AVANCÉES")
        print("-" * 20)
        
        # VAD (Voice Activity Detection)
        print("1. Détection d'activité vocale (VAD)")
        print("   💡 Filtre automatiquement les silences")
        vad_choice = input("   Activer VAD ? (o/N) : ").strip().lower()
        use_vad = vad_choice == 'o'
        
        # Format de sortie
        print("\n2. Format de sortie")
        print("   1️⃣  TXT seulement (texte brut)")
        print("   2️⃣  SRT seulement (sous-titres)")  
        print("   3️⃣  TXT + SRT (les deux)")
        
        while True:
            format_choice = input("   Format de sortie (1-3, défaut 3) : ").strip()
            if format_choice in ['1', '2', '3', '']:
                break
            print("   ❌ Veuillez choisir 1, 2 ou 3")
        
        output_format = format_choice if format_choice else '3'
        
        return {
            'use_vad': use_vad,
            'output_format': output_format
        }

    def download_media(self, url: str, out_dir: Path) -> Path:
        """Télécharge la vidéo depuis YouTube avec barre de progression"""
        out_tpl = str(out_dir / "%(title).200B.%(ext)s")
        
        progress_hook = ProgressHook()
        
        ydl_opts = {
            "outtmpl": out_tpl,
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [progress_hook],
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            fn = ydl.prepare_filename(info)
        
        return Path(fn)

    def extract_wav(self, input_path: Path, out_dir: Path) -> Path:
        """Extrait l'audio en format WAV mono 16kHz - méthode simple qui fonctionne"""
        wav_path = out_dir / (input_path.stem + ".wav")
        
        print(f"🎵 Extraction audio de : {input_path.name}")
        
        # Utilise la même méthode que votre code fonctionnel
        try:
            (
                ffmpeg
                .input(str(input_path))
                .output(str(wav_path), ac=1, ar=16000, format="wav", loglevel="error")
                .overwrite_output()
                .run(cmd=self.ffmpeg_path)
            )
            print("✅ Audio extrait avec succès")
            return wav_path
            
        except Exception as e:
            print(f"❌ Erreur extraction audio : {e}")
            print(f"💡 Vérifiez que FFmpeg est accessible : {self.ffmpeg_path}")
            sys.exit(1)

    def format_timestamp_srt(self, seconds: float) -> str:
        """Formate un timestamp au format SRT"""
        ms = int(round(seconds * 1000))
        h = ms // 3_600_000
        ms %= 3_600_000
        m = ms // 60_000
        ms %= 60_000
        s = ms // 1000
        ms %= 1000
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def write_srt(self, segments, srt_path: Path):
        """Génère le fichier SRT"""
        with open(srt_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, start=1):
                start = self.format_timestamp_srt(seg.start)
                end = self.format_timestamp_srt(seg.end)
                text = seg.text.strip()
                text = re.sub(r"\s+", " ", text)
                f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

    def transcribe_and_save(self, wav_path: Path, model_name: str, language: str, 
                           options: dict, output_dir: Path, base_name: str):
        """Effectue la transcription et sauvegarde"""
        
        # Chargement du modèle avec spinner
        self.progress_tracker.start_spinner(f"Chargement du modèle {model_name}...")
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        self.progress_tracker.stop_spinner()
        print(f"✅ Modèle {model_name} chargé")
        
        print(f"▶️ Transcription en cours avec modèle '{model_name}' sur CPU...")
        
        # Configuration de la transcription
        transcribe_params = {
            "language": language,
            "beam_size": 5,
        }
        
        if options['use_vad']:
            transcribe_params.update({
                "vad_filter": True,
                "vad_parameters": dict(min_silence_duration_ms=500)
            })
        
        # Première transcription pour info
        segments, info = model.transcribe(str(wav_path), **transcribe_params)
        
        # Chemins de sortie
        txt_path = output_dir / f"{base_name}.txt"
        srt_path = output_dir / f"{base_name}.srt"
        
        # Génération TXT
        if options['output_format'] in ['1', '3']:
            print("💾 Génération du fichier TXT...")
            with open(txt_path, "w", encoding="utf-8") as f:
                for seg in tqdm(segments, desc="TXT", unit="segment"):
                    f.write(seg.text.strip() + " ")
        
        # Génération SRT (nouvelle transcription car generator consommé)
        if options['output_format'] in ['2', '3']:
            print("💾 Génération du fichier SRT...")
            segments, _ = model.transcribe(str(wav_path), **transcribe_params)
            self.write_srt(list(tqdm(segments, desc="SRT", unit="segment")), srt_path)
        
        return txt_path, srt_path, info

    def run(self):
        """Lance l'interface principale"""
        self.display_header()
        
        try:
            # Choix de la source
            source_choice = self.get_source_choice()
            
            if source_choice == '1':
                source_path = self.get_local_file()
            else:
                source_path = self.get_youtube_url()
            
            # Configuration
            model_name = self.get_model_choice()
            language = self.get_language_choice()
            options = self.get_advanced_options()
            
            # Préparation des dossiers
            output_dir = Path("transcriptions")
            output_dir.mkdir(exist_ok=True)
            
            print("\n" + "="*60)
            print("🚀 DÉBUT DE LA TRANSCRIPTION")
            print("="*60)
            
            start_time = time.time()
            
            # Traitement
            with tempfile.TemporaryDirectory() as tmpd:
                tmp_dir = Path(tmpd)
                
                if self.is_url(source_path):
                    media_file = self.download_media(source_path, tmp_dir)
                    base_name = re.sub(r'[<>:"/\\|?*]', '_', media_file.stem)
                else:
                    media_file = Path(source_path)
                    base_name = media_file.stem
                
                # Extraction audio
                wav_file = self.extract_wav(media_file, tmp_dir)
                
                # Transcription
                txt_path, srt_path, info = self.transcribe_and_save(
                    wav_file, model_name, language, options, output_dir, base_name
                )
            
            # Calcul du temps total
            total_time = time.time() - start_time
            minutes, seconds = divmod(int(total_time), 60)
            
            # Résultat final
            print("\n" + "="*60)
            print("🎉 TRANSCRIPTION TERMINÉE")
            print("="*60)
            
            if options['output_format'] in ['1', '3']:
                print(f"📄 Fichier TXT : {txt_path}")
            if options['output_format'] in ['2', '3']:
                print(f"🎬 Fichier SRT : {srt_path}")
                
            print(f"🌍 Langue détectée : {info.language}")
            print(f"📊 Confiance : {info.language_probability:.1%}")
            print(f"⏱️  Temps total : {minutes:02d}:{seconds:02d}")
            print(f"📁 Dossier de sortie : {output_dir.absolute()}")
            
        except KeyboardInterrupt:
            print("\n⏹️  Transcription interrompue par l'utilisateur")
        except Exception as e:
            print(f"\n❌ Erreur : {e}")
            print("💡 Vérifiez vos paramètres et réessayez")

def main():
    transcriber = VideoTranscriber()
    transcriber.run()

if __name__ == "__main__":
    main()