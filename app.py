import os
import uuid
import threading
import subprocess
import shlex
from pathlib import Path
from flask import Flask, request, render_template, jsonify, send_file, abort

# Config
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("sorties")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Configuration FFmpeg - utilise le même chemin que dans transcribe.py
FFMPEG_PATH = r"C:\AllProjects\transcipt_video\ffmpeg-master-latest-win64-gpl-shared\ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.exe"
FFPROBE_PATH = r"C:\AllProjects\transcipt_video\ffmpeg-master-latest-win64-gpl-shared\ffmpeg-master-latest-win64-gpl-shared\bin\ffprobe.exe"

# Vérifier si les chemins existent, sinon utiliser les versions système
if not os.path.exists(FFMPEG_PATH):
    FFMPEG_PATH = "ffmpeg"  # Version système
if not os.path.exists(FFPROBE_PATH):
    FFPROBE_PATH = "ffprobe"  # Version système

app = Flask(__name__)

# Jobs state: job_id -> {"status": "queued|running|done|error", "progress": 0-100, "txt": path or None, "msg": error}
jobs = {}

def get_duration(path: Path) -> float:
    """Obtient la durée du fichier média en secondes"""
    try:
        if os.path.exists(FFPROBE_PATH) and FFPROBE_PATH.endswith('.exe'):
            # Utilise le chemin complet vers ffprobe
            cmd = [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration', 
                   '-of', 'default=noprint_wrappers=1:nokey=1', str(path)]
        else:
            # Utilise ffprobe système
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                   '-of', 'default=noprint_wrappers=1:nokey=1', str(path)]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
        else:
            print(f"Erreur ffprobe: {result.stderr}")
            return 0.0
    except Exception as e:
        print(f"Erreur lors de l'obtention de la durée: {e}")
        return 0.0

def extract_wav(input_path: Path, out_path: Path):
    """Extrait l'audio en format WAV mono 16kHz"""
    try:
        if os.path.exists(FFMPEG_PATH) and FFMPEG_PATH.endswith('.exe'):
            # Utilise le chemin complet vers ffmpeg
            cmd = [FFMPEG_PATH, '-y', '-i', str(input_path), '-ac', '1', '-ar', '16000', 
                   '-vn', str(out_path), '-loglevel', 'error']
        else:
            # Utilise ffmpeg système
            cmd = ['ffmpeg', '-y', '-i', str(input_path), '-ac', '1', '-ar', '16000',
                   '-vn', str(out_path), '-loglevel', 'error']
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise Exception(f"Erreur FFmpeg: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        raise Exception("Timeout lors de l'extraction audio (5 minutes)")
    except Exception as e:
        raise Exception(f"Erreur lors de l'extraction audio: {e}")

def transcribe_job(job_id: str, source_path: Path, language: str = None, model_name: str = "small", vad: bool = False):
    """Worker de transcription qui s'exécute en arrière-plan"""
    try:
        from faster_whisper import WhisperModel
        
        jobs[job_id]["status"] = "running"
        jobs[job_id]["progress"] = 5
        
        # Extraction audio
        wav = OUTPUT_DIR / f"{job_id}.wav"
        extract_wav(source_path, wav)
        jobs[job_id]["progress"] = 15
        
        # Obtention de la durée totale pour le calcul de progression
        total_dur = get_duration(source_path) or 0.0
        
        # Chargement du modèle Whisper
        print(f"Chargement du modèle {model_name}...")
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        jobs[job_id]["progress"] = 25
        
        # Configuration de la transcription
        transcribe_params = {
            "language": language if language else None,
            "beam_size": 5,
        }
        
        if vad:
            transcribe_params.update({
                "vad_filter": True,
                "vad_parameters": dict(min_silence_duration_ms=500)
            })
        
        # Transcription
        print(f"Début de la transcription avec {model_name}...")
        segments, info = model.transcribe(str(wav), **transcribe_params)
        
        # Sauvegarde du texte
        txt_path = OUTPUT_DIR / f"{job_id}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            last_progress = 25
            for seg in segments:
                text = " ".join(seg.text.strip().split())
                
                # Formatage du timestamp [HH:MM:SS]
                h = int(seg.end // 3600)
                m = int((seg.end % 3600) // 60)
                s = int(seg.end % 60)
                timestamp = f"[{h:02d}:{m:02d}:{s:02d}]"
                
                f.write(f"{text} {timestamp}\n")
                
                # Mise à jour de la progression
                if total_dur > 0:
                    current_progress = min(95, int(25 + (seg.end / total_dur * 70)))
                    if current_progress > last_progress:
                        jobs[job_id]["progress"] = current_progress
                        last_progress = current_progress
        
        # Nettoyage du fichier WAV temporaire
        try:
            wav.unlink()
        except:
            pass
            
        # Finalisation
        jobs[job_id]["progress"] = 100
        jobs[job_id]["status"] = "done"
        jobs[job_id]["txt"] = str(txt_path)
        jobs[job_id]["language"] = getattr(info, "language", "unknown")
        
        print(f"Transcription terminée pour job {job_id}")
        
    except Exception as e:
        print(f"Erreur dans transcribe_job: {e}")
        jobs[job_id]["status"] = "error"
        jobs[job_id]["msg"] = str(e)
        
        # Nettoyage en cas d'erreur
        try:
            wav = OUTPUT_DIR / f"{job_id}.wav"
            if wav.exists():
                wav.unlink()
        except:
            pass

@app.route("/")
def index():
    """Page d'accueil"""
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    """Endpoint d'upload de fichier"""
    try:
        file = request.files.get("file")
        if not file or not file.filename:
            return jsonify({"error": "Aucun fichier fourni"}), 400
        
        # Génération d'un ID unique pour le job
        job_id = uuid.uuid4().hex
        
        # Sauvegarde sécurisée du fichier
        filename = file.filename
        # Nettoyage du nom de fichier
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        saved_path = UPLOAD_DIR / f"{job_id}_{safe_filename}"
        file.save(saved_path)
        
        # Initialisation du job
        jobs[job_id] = {
            "status": "queued", 
            "progress": 0, 
            "txt": None, 
            "msg": None,
            "filename": safe_filename
        }
        
        # Récupération des paramètres
        model = request.form.get("model", "small")
        language = request.form.get("language", "").strip() or None
        vad = request.form.get("vad", "false").lower() == "true"
        
        print(f"Nouveau job {job_id}: {safe_filename}, modèle: {model}, langue: {language}, VAD: {vad}")
        
        # Démarrage du thread de transcription
        thread = threading.Thread(
            target=transcribe_job, 
            args=(job_id, saved_path, language, model, vad),
            daemon=True
        )
        thread.start()
        
        return jsonify({"job_id": job_id, "filename": safe_filename})
        
    except Exception as e:
        print(f"Erreur upload: {e}")
        return jsonify({"error": f"Erreur lors de l'upload: {str(e)}"}), 500

@app.route("/status/<job_id>")
def status(job_id):
    """Endpoint de vérification du statut"""
    info = jobs.get(job_id)
    if not info:
        return jsonify({"error": "Job inconnu"}), 404
    
    # Retourne seulement les informations nécessaires
    return jsonify({
        "status": info["status"],
        "progress": info.get("progress", 0),
        "msg": info.get("msg"),
        "language": info.get("language")
    })

@app.route("/download/<job_id>")
def download(job_id):
    """Endpoint de téléchargement de la transcription"""
    info = jobs.get(job_id)
    if not info or info.get("status") != "done" or not info.get("txt"):
        return abort(404)
    
    txt_path = Path(info["txt"])
    if not txt_path.exists():
        return abort(404)
    
    # Nom de fichier de téléchargement
    original_name = info.get("filename", "transcription")
    download_name = f"transcription_{Path(original_name).stem}.txt"
    
    return send_file(txt_path, as_attachment=True, download_name=download_name)

if __name__ == "__main__":
    print("🚀 Démarrage du serveur de transcription...")
    print(f"📁 Dossier uploads: {UPLOAD_DIR.absolute()}")
    print(f"📁 Dossier sorties: {OUTPUT_DIR.absolute()}")
    print(f"🔧 FFmpeg: {FFMPEG_PATH}")
    print(f"🔧 FFprobe: {FFPROBE_PATH}")
    print("🌐 Interface disponible sur: http://localhost:5000")
    print("-" * 50)
    
    app.run(debug=True, port=5000, host="0.0.0.0")