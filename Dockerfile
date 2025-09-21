FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg git build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV WHISPER_MODEL_SIZE=small
ENV WHISPER_COMPUTE_TYPE=int8
ENV WHISPER_CPU_THREADS=4
ENV PORT=8000

EXPOSE 8000
CMD ["python", "app.py"]
