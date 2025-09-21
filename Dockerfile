# Imagem leve com Python e apt
FROM python:3.11-slim

# Instala ffmpeg e dependências do faster-whisper (pytorch roda só CPU nesse caso)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg git build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código
COPY . .

# Variáveis padrão (podem ser sobrescritas no Render)
ENV WHISPER_MODEL_SIZE=small
ENV WHISPER_COMPUTE_TYPE=int8
ENV WHISPER_CPU_THREADS=4

# Flask
ENV PORT=8000

EXPOSE 8000
CMD ["python", "app.py"]
