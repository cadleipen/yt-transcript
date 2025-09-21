import os
from flask import Flask, request, jsonify
from transcriber import process_video

app = Flask(__name__)

@app.get("/health")
def health():
    return {"ok": True, "service": "youtube-transcriber"}

@app.post("/transcribe")
def transcribe_endpoint():
    data = request.get_json(silent=True) or {}
    video_url = data.get("video_url") or request.args.get("video_url")
    if not video_url:
        return jsonify({"error": "Informe 'video_url' no JSON ou query string"}), 400

    # Parâmetros opcionais
    language = data.get("language")  # ex: "pt" para forçar PT-BR
    model_size = data.get("model_size")  # ex: "small"
    extra_meta = data.get("meta", {})

    try:
        result = process_video(
            video_url=video_url,
            force_language=language,
            model_size=model_size,
            extra_meta=extra_meta,
            send_to_make=True  # envia ao Make
        )
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
