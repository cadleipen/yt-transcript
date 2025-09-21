# YouTube → Áudio → Texto → Make (Webhook)

Este projeto baixa o áudio de um vídeo do YouTube com `yt-dlp`, transcreve com `faster-whisper` e envia o resultado para um **Webhook do Make**.

## Variáveis de ambiente
- `MAKE_WEBHOOK_URL` (obrigatória): URL do webhook do Make (Integromat).
- `YTDLP_COOKIES_B64` (opcional): cookies em Base64 (formato Netscape) para vídeos com restrição.
- `WHISPER_MODEL_SIZE` (opcional): tiny, base, small, medium, large-v3 (padrão `small`).
- `WHISPER_COMPUTE_TYPE` (opcional): int8, float16, int8_float16, int8_float32 (padrão `int8`).
- `WHISPER_CPU_THREADS` (opcional): threads CPU (padrão 4).

## Uso no Render (Web Service)
1. Conecte este repositório no Render e **deploy** com `render.yaml`.
2. Configure as env vars no painel (pelo menos `MAKE_WEBHOOK_URL`).
3. Faça uma requisição:
