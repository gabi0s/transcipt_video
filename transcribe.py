import os
import re
import sys
import time
import threading
import tempfile
from pathlib import Path

import ffmpeg
from faster_whisper import WhisperModel
from tqdm import tqdm
from yt_dlp import YoutubeDL

class ProgressTracker:
    def __init__(self):
        self.stop_animation = False
        self.animation_thread = None

    def start_spinner(self, message: str):
        self.stop_animation = False
        self.animation_thread = threading.Thread(target=self._animate_spinner, args=(message,), daemon=True)
        self.animation_thread.start()

    def stop_spinner(self):
        self.stop_animation = True
        if self.animation_thread:
            self.animation_thread.join()
        print()

    def _animate_spinner(self, message: str):
        spinner = ['⠋','⠙','⠹','⠸','⠼','⠴','⠦','⠧','⠇','⠏']
        i = 0
        while not self.stop_animation:
            print(f'\r{spinner[i]} {message}', end='', flush=True)
            i = (i + 1) % len(spinner)
            time.sleep(0.1)

class ProgressHook:
    def __init__(self):
        self.pbar = None

    def __call__(self, d):
        if d['status'] == 'downloading':
            if self.pbar is None:
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                self.pbar = tqdm(
                    total=total, unit='B', unit_scale=True,
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
        # Utilise un binaire FFmpeg depuis PATH (ou var d'env), avec fallback optionnel
        self.ffmpeg_bin = os.environ.get("FFMPEG_BIN", "ffmpeg")
        self.supported_formats = ['.mp4','.mkv','.mov','.avi','.mp3','.wav','.m4a','.flac','.webm']
        self.whisper_models = {
            'tiny': 'Très rapide, précision basique (39 MB)',
            'base': 'Rapide, précision correcte (74 MB)',
            'small': 'Équilibré vitesse/précision (244 MB)',
            'medium': 'Lent, bonne précision (769 MB)',
            'large-v3': 'Très lent, meilleure précision (1550 MB)'
        }
        self.progress_tracker = ProgressTracker()

    @staticmethod
    def is_url(s: str) -> bool:
        return s.startswith("http://") or s.startswith("https://")

    def display_header(self):
        print("=" * 60)
        print("🎥 TRANSCRIPTEUR VIDÉO/AUDIO AVANCÉ")
        print("   Conversion vidéo → texte avec suivi en temps réel")
        print("=" * 60)
        print()

    def get_source_choice(self) -> str:
        print("📂 SÉLECTION DE LA SOURCE")
        print("-" * 30)
        print("1️⃣  Fichier local")
        print("2️⃣  URL YouTube")
        print()
        while True:
            choice = input("🔽 Votre choix (1 ou 2) : ").strip()
            if choice in ['1', '2']:
                return choice
            print("❌ Veuillez saisir 1 ou 2")

    def get_local_file(self) -> str:
        print("\n📁 FICHIER LOCAL")
        print("-" * 20)
        print(f"Formats supportés : {', '.join(self.supported_formats)}\n")
        while True:
            file_path = input("📎 Chemin complet du fichier : ").strip().strip('"')
            if not file_path:
                print("❌ Veuillez saisir un chemin de fichier")
                continue
            self.progress_tracker.start_spinner("Vérification du fichier...")
            time.sleep(0.4)
            if not os.path.exists(file_path):
                self.progress_tracker.stop_spinner()
                print(f"❌ Fichier introuvable : {file_path}")
                continue
            ext = Path(file_path).suffix.lower()
            if ext not in self.supported_formats:
                self.progress_tracker.stop_spinner()
                print(f"❌ Format non supporté : {ext}")
                continue
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            self.progress_tracker.stop_spinner()
            print(f"✅ Fichier valide : {Path(file_path).name} ({size_mb:.1f} MB)")
            return file_path

    def get_youtube_url(self) -> str:
        print("\n🌐 URL YOUTUBE")
        print("-" * 15)
        print("💡 Formats acceptés : youtube.com, youtu.be, etc.\n")
        while True:
            url = input("🔗 Collez l'URL YouTube : ").strip()
            if not url:
                print("❌ Veuillez saisir une URL")
                continue
            if not self.is_url(url):
                print("❌ URL invalide (http/https)")
                continue
            self.progress_tracker.start_spinner("Vérification de l'URL...")
            try:
                with YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                self.progress_tracker.stop_spinner()
                title = info.get('title', 'Titre non disponible')
                duration = info.get('duration', 0) or 0
                print(f"✅ Vidéo trouvée : {title}")
                if duration:
                    m, s = divmod(duration, 60)
                    print(f"   ⏱️  Durée : {m:02d}:{s:02d}")
                return url
            except Exception as e:
                self.progress_tracker.stop_spinner()
                print(f"❌ Erreur URL : {e}")

    def get_model_choice(self) -> str:
        print("\n🧠 MODÈLE DE TRANSCRIPTION")
        print("-" * 30)
        for i, (model, desc) in enumerate(self.whisper_models.items(), 1):
            print(f"{i}️⃣  {model.ljust(10)} - {desc}")
        print("6️⃣  Défaut recommandé (small)\n")
        while True:
            choice = input("🔽 Votre choix (1-6) : ").strip()
            if choice in ("", "6"):
                return "small"
            try:
                n = int(choice)
                if 1 <= n <= 5:
                    return list(self.whisper_models.keys())[n - 1]
            except ValueError:
                pass
            print("❌ Veuillez choisir entre 1 et 6")

    def get_language_choice(self) -> str:
        print("\n🌍 LANGUE DE TRANSCRIPTION")
        print("-" * 25)
        common = {
            'fr': 'Français', 'en': 'Anglais', 'es': 'Espagnol',
            'de': 'Allemand', 'it': 'Italien', 'pt': 'Portugais', 'auto': 'Détection automatique'
        }
        for i, (code, name) in enumerate(common.items(), 1):
            print(f"{i}️⃣  {name} ({code})")
        print(f"{len(common) + 1}️⃣  Autre langue (code ISO)\n")
        while True:
            choice = input("🔽 Votre choix : ").strip()
            if not choice or choice == str(len(common)):  # auto
                return None
            try:
                n = int(choice)
                if 1 <= n <= len(common):
                    code = list(common.keys())[n - 1]
                    return None if code == 'auto' else code
                if n == len(common) + 1:
                    code = input("Code langue ISO (ex: ja, zh, ru) : ").strip().lower()
                    return code or None
            except ValueError:
                if len(choice) == 2 and choice.isalpha():
                    return choice.lower()
            print("❌ Saisie invalide")

    def get_advanced_options(self) -> dict:
        print("\n⚙️  OPTIONS AVANCÉES")
        print("-" * 20)
        vad_choice = input("Activer la détection d'activité vocale (VAD) ? (o/N) : ").strip().lower()
        use_vad = vad_choice == 'o'
        print("\nFormats de sortie : 1) TXT  2) SRT  3) TXT+SRT (défaut)")
        while True:
            f = input("Format de sortie (1-3, défaut 3) : ").strip()
            if f in ("", "1", "2", "3"):
                break
        return {"use_vad": use_vad, "output_format": f or "3"}

    def download_media(self, url: str, out_dir: Path) -> Path:
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
        wav_path = out_dir / (input_path.stem + ".wav")
        print(f"🎵 Extraction audio de : {input_path.name}")
        try:
            (
                ffmpeg
                .input(str(input_path))
                .output(str(wav_path), ac=1, ar=16000, format="wav", loglevel="error")
                .overwrite_output()
                .run(cmd=self.ffmpeg_bin)
            )
            print("✅ Audio extrait avec succès")
            return wav_path
        except Exception as e:
            print(f"❌ Erreur extraction audio : {e}")
            print(f"💡 Vérifiez que FFmpeg est accessible (PATH ou FFMPEG_BIN).")
            sys.exit(1)

    @staticmethod
    def format_timestamp_srt(seconds: float) -> str:
        ms = int(round(seconds * 1000))
        h, ms = divmod(ms, 3_600_000)
        m, ms = divmod(ms, 60_000)
        s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def write_srt(self, segments, srt_path: Path):
        with open(srt_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, start=1):
                start = self.format_timestamp_srt(seg.start)
                end = self.format_timestamp_srt(seg.end)
                text = re.sub(r"\s+", " ", seg.text.strip())
                f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

    def transcribe_and_save(self, wav_path: Path, model_name: str, language: str,
                            options: dict, output_dir: Path, base_name: str):
        self.progress_tracker.start_spinner(f"Chargement du modèle {model_name}...")
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        self.progress_tracker.stop_spinner()
        print(f"✅ Modèle {model_name} chargé")
        print(f"▶️ Transcription en cours...")

        params = {"language": language, "beam_size": 5}
        if options['use_vad']:
            params.update({"vad_filter": True, "vad_parameters": dict(min_silence_duration_ms=500)})

        # Effectue une seule transcription et met en cache la liste des segments
        seg_iter, info = model.transcribe(str(wav_path), **params)
        segments = list(seg_iter)  # évite une 2e passe couteuse

        txt_path = output_dir / f"{base_name}.txt"
        srt_path = output_dir / f"{base_name}.srt"

        if options['output_format'] in ['1', '3']:
            print("💾 Génération du fichier TXT...")
            with open(txt_path, "w", encoding="utf-8") as f:
                for seg in tqdm(segments, desc="TXT", unit="segment"):
                    f.write(seg.text.strip() + " ")

        if options['output_format'] in ['2', '3']:
            print("💾 Génération du fichier SRT...")
            self.write_srt(list(tqdm(segments, desc="SRT", unit="segment")), srt_path)

        return txt_path, srt_path, info

    def run(self):
        self.display_header()
        try:
            source_choice = self.get_source_choice()
            source_path = self.get_local_file() if source_choice == '1' else self.get_youtube_url()
            model_name = self.get_model_choice()
            language = self.get_language_choice()
            options = self.get_advanced_options()

            output_dir = Path("transcriptions"); output_dir.mkdir(exist_ok=True)

            print("\n" + "="*60)
            print("🚀 DÉBUT DE LA TRANSCRIPTION")
            print("="*60)

            start_time = time.time()

            with tempfile.TemporaryDirectory() as tmpd:
                tmp_dir = Path(tmpd)
                if self.is_url(source_path):
                    media_file = self.download_media(source_path, tmp_dir)
                    base_name = re.sub(r'[<>:"/\\|?*]', '_', media_file.stem)
                else:
                    media_file = Path(source_path)
                    base_name = media_file.stem

                wav_file = self.extract_wav(media_file, tmp_dir)
                txt_path, srt_path, info = self.transcribe_and_save(
                    wav_file, model_name, language, options, output_dir, base_name
                )

            total_time = time.time() - start_time
            minutes, seconds = divmod(int(total_time), 60)

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
    VideoTranscriber().run()

if __name__ == "__main__":
    main()
