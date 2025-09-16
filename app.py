import os
import uuid
import threading
import subprocess
from pathlib import Path
from flask import Flask, request, render_template, jsonify, send_file, abort

# Dossiers d'E/S
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("sorties")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# FFmpeg/ffprobe : on privilégie le PATH, avec fallback éventuel via variables d'env
FFMPEG_PATH = os.environ.get("FFMPEG_BIN", "ffmpeg")
FFPROBE_PATH = os.environ.get("FFPROBE_BIN", "ffprobe")

app = Flask(__name__)

# Jobs state: job_id -> {...}
jobs = {}

def get_duration(path: Path) -> float:
    """Durée du média en secondes (via ffprobe)."""
    try:
        cmd = [FFPROBE_PATH, "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
        return 0.0
    except Exception:
        return 0.0

def extract_wav(input_path: Path, out_path: Path):
    """Extrait l'audio en WAV mono 16kHz (silencieux)."""
    cmd = [FFMPEG_PATH, "-y", "-i", str(input_path), "-ac", "1", "-ar", "16000",
           "-vn", str(out_path), "-loglevel", "error"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "FFmpeg error")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Timeout lors de l'extraction audio (5 minutes)")

def transcribe_job(job_id: str, source_path: Path, language: str = None,
                   model_name: str = "small", vad: bool = False):
    """Worker de transcription (thread)."""
    try:
        from faster_whisper import WhisperModel

        jobs[job_id]["status"] = "running"
        jobs[job_id]["progress"] = 5

        # 1) Extraction audio
        wav = OUTPUT_DIR / f"{job_id}.wav"
        extract_wav(source_path, wav)
        jobs[job_id]["progress"] = 15

        total_dur = get_duration(source_path) or 0.0

        # 2) Chargement modèle
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        jobs[job_id]["progress"] = 25

        # 3) Transcription
        params = {"language": language or None, "beam_size": 5}
        if vad:
            params.update({"vad_filter": True, "vad_parameters": dict(min_silence_duration_ms=500)})

        segments, info = model.transcribe(str(wav), **params)

        # 4) Sauvegarde texte (+ progression)
        txt_path = OUTPUT_DIR / f"{job_id}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            last = 25
            for seg in segments:
                text = " ".join(seg.text.strip().split())
                h = int(seg.end // 3600); m = int((seg.end % 3600) // 60); s = int(seg.end % 60)
                f.write(f"{text} [{h:02d}:{m:02d}:{s:02d}]\n")
                if total_dur > 0:
                    cur = min(95, int(25 + (seg.end / total_dur * 70)))
                    if cur > last:
                        jobs[job_id]["progress"] = cur
                        last = cur

        # Nettoyage
        try: wav.unlink()
        except: pass

        jobs[job_id].update({
            "status": "done",
            "progress": 100,
            "txt": str(txt_path),
            "language": getattr(info, "language", "unknown")
        })

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["msg"] = str(e)
        try:
            wav = OUTPUT_DIR / f"{job_id}.wav"
            if wav.exists(): wav.unlink()
        except: pass

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    try:
        file = request.files.get("file")
        if not file or not file.filename:
            return jsonify({"error": "Aucun fichier fourni"}), 400

        job_id = uuid.uuid4().hex

        # Nom de fichier nettoyé
        safe = "".join(c for c in file.filename if c.isalnum() or c in (" ", "-", "_", ".")).rstrip()
        saved = UPLOAD_DIR / f"{job_id}_{safe}"
        file.save(saved)

        jobs[job_id] = {"status": "queued", "progress": 0, "txt": None, "msg": None, "filename": safe}

        model = request.form.get("model", "small")
        language = (request.form.get("language") or "").strip() or None
        vad = (request.form.get("vad", "false").lower() == "true")

        threading.Thread(
            target=transcribe_job, args=(job_id, saved, language, model, vad), daemon=True
        ).start()

        return jsonify({"job_id": job_id, "filename": safe})

    except Exception as e:
        return jsonify({"error": f"Erreur lors de l'upload: {str(e)}"}), 500

@app.route("/status/<job_id>")
def status(job_id):
    info = jobs.get(job_id)
    if not info:
        return jsonify({"error": "Job inconnu"}), 404
    return jsonify({
        "status": info["status"],
        "progress": info.get("progress", 0),
        "msg": info.get("msg"),
        "language": info.get("language")
    })

@app.route("/download/<job_id>")
def download(job_id):
    info = jobs.get(job_id)
    if not info or info.get("status") != "done" or not info.get("txt"):
        return abort(404)
    txt_path = Path(info["txt"])
    if not txt_path.exists():
        return abort(404)
    original_name = info.get("filename", "transcription")
    download_name = f"transcription_{Path(original_name).stem}.txt"
    return send_file(txt_path, as_attachment=True, download_name=download_name)

if __name__ == "__main__":
    print("🚀 Démarrage du serveur de transcription...")
    print(f"📁 Dossier uploads: {UPLOAD_DIR.absolute()}")
    print(f"📁 Dossier sorties: {OUTPUT_DIR.absolute()}")
    print(f"🔧 FFmpeg: {FFMPEG_PATH}")
    print(f"🔧 FFprobe: {FFPROBE_PATH}")
    print("🌐 Interface: http://localhost:5000")
    print("-" * 50)
    app.run(debug=True, port=5000, host="0.0.0.0")
