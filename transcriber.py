import os
import base64
import json
import shutil
import subprocess
import tempfile
import uuid
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List

# ===============================
# Utilidades
# ===============================

def write_cookies_if_any() -> Optional[Path]:
    """
    Se YTDLP_COOKIES_B64 estiver setada, salva cookies.txt e retorna o path.
    """
    b64 = os.getenv("YTDLP_COOKIES_B64", "").strip()
    if not b64:
        return None
    cookies_path = Path(tempfile.gettempdir()) / f"cookies_{uuid.uuid4().hex}.txt"
    data = base64.b64decode(b64)
    cookies_path.write_bytes(data)
    return cookies_path

def run(cmd: List[str], cwd: Optional[str] = None) -> None:
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Erro ao executar: {' '.join(cmd)}\nSaída:\n{p.stdout}")

def ytdlp_download_audio(video_url: str, out_dir: Path, cookies_file: Optional[Path]) -> Path:
    """
    Baixa o melhor áudio disponível em .mp3 (ou m4a se mais rápido), retorna caminho do arquivo.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    # Saída ex.: audio.<ext>
    out_tpl = str(out_dir / "audio.%(ext)s")
    cmd = [
        "yt-dlp",
        "-f", "bestaudio",
        "--no-warnings",
        "--no-progress",
        "--restrict-filenames",
        "-x", "--audio-format", "mp3",
        "-o", out_tpl,
        video_url
    ]
    if cookies_file:
        cmd += ["--cookies", str(cookies_file)]
    run(cmd)

    # Procura arquivo gerado (audio.mp3)
    for ext in ("mp3", "m4a", "webm", "opus"):
        f = out_dir / f"audio.{ext}"
        if f.exists():
            return f
    # fallback: pega o primeiro arquivo no diretório
    files = list(out_dir.glob("*"))
    if not files:
        raise RuntimeError("Nenhum arquivo de áudio baixado.")
    return files[0]

# ===============================
# Transcrição com faster-whisper
# ===============================

def transcribe(audio_path: Path, language: Optional[str] = None, model_size: Optional[str] = None) -> Dict[str, Any]:
    """
    Transcreve com faster-whisper. Retorna dict com texto, segmentos e metadados.
    """
    from faster_whisper import WhisperModel

    model_size = model_size or os.getenv("WHISPER_MODEL_SIZE", "small")  # tiny/base/small/medium/large-v3
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")  # "int8", "float16", "int8_float16", "int8_float32"
    num_workers = int(os.getenv("WHISPER_CPU_THREADS", "4"))

    model = WhisperModel(model_size, device="cpu", compute_type=compute_type, cpu_threads=num_workers)

    segments, info = model.transcribe(
        str(audio_path),
        language=language,             # None = auto-detecção
        beam_size=int(os.getenv("WHISPER_BEAM_SIZE", "5")),
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        condition_on_previous_text=True
    )

    segs = []
    full_text_parts = []
    for s in segments:
        segs.append({
            "start": float(s.start),
            "end": float(s.end),
            "text": s.text.strip()
        })
        full_text_parts.append(s.text.strip())

    return {
        "model": model_size,
        "language": info.language,
        "language_probability": float(info.language_probability or 0.0),
        "duration": float(info.duration or 0.0),
        "text": " ".join(full_text_parts).strip(),
        "segments": segs
    }

# ===============================
# Envio para o Make (Webhook)
# ===============================

def post_to_make(payload: Dict[str, Any]) -> requests.Response:
    webhook_url = os.getenv("MAKE_WEBHOOK_URL", "").strip()
    if not webhook_url:
        raise RuntimeError("Defina MAKE_WEBHOOK_URL nas variáveis de ambiente.")
    headers = {"Content-Type": "application/json"}
    return requests.post(webhook_url, headers=headers, data=json.dumps(payload), timeout=60)

# ===============================
# Pipeline
# ===============================

def process_video(
    video_url: str,
    force_language: Optional[str] = None,
    model_size: Optional[str] = None,
    extra_meta: Optional[Dict[str, Any]] = None,
    send_to_make: bool = True
) -> Dict[str, Any]:
    """
    Baixa áudio, transcreve e (opcionalmente) envia ao Make.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="yt_transc_"))
    cookies_file = None
    try:
        cookies_file = write_cookies_if_any()
        audio_path = ytdlp_download_audio(video_url, tmp_dir, cookies_file)

        result = transcribe(audio_path, language=force_language, model_size=model_size)

        payload = {
            "source": "youtube-transcriber",
            "video_url": video_url,
            "model": result["model"],
            "language": result["language"],
            "language_probability": result["language_probability"],
            "duration": result["duration"],
            "text": result["text"],
            "segments": result["segments"],
        }
        if extra_meta:
            payload["meta"] = extra_meta

        if send_to_make:
            r = post_to_make(payload)
            payload["make_status_code"] = r.status_code
            try:
                payload["make_response"] = r.json()
            except Exception:
                payload["make_response"] = r.text

        return payload

    finally:
        if cookies_file and cookies_file.exists():
            try: cookies_file.unlink()
            except Exception: pass
        shutil.rmtree(tmp_dir, ignore_errors=True)
