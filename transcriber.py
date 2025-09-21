import os
import shutil
import subprocess
import tempfile
import uuid
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List

# ===============================
# Funções utilitárias
# ===============================

def run(cmd: List[str], cwd: Optional[str] = None) -> None:
    """Executa um comando de shell e lança erro se falhar."""
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Erro ao executar: {' '.join(cmd)}\nSaída:\n{p.stdout}")

def write_cookies_if_any() -> Optional[Path]:
    """
    Se a env YTDLP_COOKIES_B64 estiver definida, decodifica e salva em um arquivo temporário.
    Retorna o caminho do arquivo de cookies ou None.
    """
    b64 = os.getenv("YTDLP_COOKIES_B64", "").strip()
    if not b64:
        return None
    cookies_path = Path(tempfile.gettempdir()) / f"cookies_{uuid.uuid4().hex}.txt"
    cookies_path.write_bytes(base64.b64decode(b64))
    return cookies_path

def ytdlp_download_audio(video_url: str, out_dir: Path, cookies_file: Optional[Path] = None) -> Path:
    """
    Baixa o áudio do YouTube com yt-dlp e retorna o caminho do arquivo gerado.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out_tpl = str(out_dir / "audio.%(ext)s")

    cmd = [
        "yt-dlp", "-f", "bestaudio",
        "--no-warnings", "--no-progress",
        "--restrict-filenames",
        "-x", "--audio-format", "mp3",
        "-o", out_tpl,
        # ajuda a evitar alguns bloqueios de player
        "--extractor-args", "youtube:player_client=web"
    ]
    if cookies_file:
        cmd += ["--cookies", str(cookies_file)]
    cmd.append(video_url)

    run(cmd)

    # procura pelo arquivo gerado
    for ext in ("mp3", "m4a", "webm", "opus"):
        f = out_dir / f"audio.{ext}"
        if f.exists():
            return f
    files = list(out_dir.glob("*"))
    if not files:
        raise RuntimeError("Nenhum arquivo de áudio baixado.")
    return files[0]

# ===============================
# Transcrição com faster-whisper
# ===============================

def transcribe(audio_path: Path, language: Optional[str] = None, model_size: Optional[str] = None) -> Dict[str, Any]:
    """Transcreve áudio usando faster-whisper."""
    from faster_whisper import WhisperModel

    model_size = model_size or os.getenv("WHISPER_MODEL_SIZE", "small")  # tiny/base/small/medium/large-v3
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")             # int8/float16/int8_float16/int8_float32
    num_workers = int(os.getenv("WHISPER_CPU_THREADS", "4"))

    model = WhisperModel(model_size, device="cpu", compute_type=compute_type, cpu_threads=num_workers)
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=int(os.getenv("WHISPER_BEAM_SIZE", "5")),
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        condition_on_previous_text=True
    )

    segs, full = [], []
    for s in segments:
        txt = s.text.strip()
        segs.append({"start": float(s.start), "end": float(s.end), "text": txt})
        full.append(txt)

    return {
        "model": model_size,
        "language": info.language,
        "language_probability": float(info.language_probability or 0.0),
        "duration": float(info.duration or 0.0),
        "text": " ".join(full).strip(),
        "segments": segs
    }

# ===============================
# Pipeline principal
# ===============================

def process_video(video_url: str, force_language: Optional[str] = None,
                  model_size: Optional[str] = None, extra_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Baixa áudio do vídeo, transcreve e retorna o resultado como dict.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="yt_transc_"))
    cookies_file = None
    try:
        cookies_file = write_cookies_if_any()
        audio_path = ytdlp_download_audio(video_url, tmp_dir, cookies_file)
        result = transcribe(audio_path, language=force_language, model_size=model_size)

        payload = {"source": "youtube-transcriber", "video_url": video_url, **result}
        if extra_meta:
            payload["meta"] = extra_meta
        return payload

    finally:
        try:
            if cookies_file and cookies_file.exists():
                cookies_file.unlink()
        except Exception:
            pass
        shutil.rmtree(tmp_dir, ignore_errors=True)
