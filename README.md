# YouTube → Áudio → Texto (sem webhook)

Chame `POST /transcribe` e receba a transcrição na resposta.

### Exemplo de chamada
POST https://SEU-SERVICO.onrender.com/transcribe
Content-Type: application/json
{
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "language": "pt",
  "meta": {"origem":"make"}
}

### Resposta (resumo)
{
  "ok": true,
  "result": {
    "video_url": "...",
    "model": "small",
    "language": "pt",
    "language_probability": 0.98,
    "duration": 321.4,
    "text": "transcrição completa...",
    "segments": [{ "start": 0.0, "end": 5.2, "text": "..." }]
  }
}
