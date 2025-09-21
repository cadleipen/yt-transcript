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
        return jsonify({"error": "Informe 'video_url'"}), 400

    language = data.get("language")
    model_size = data.get("model_size")
    extra_meta = data.get("meta", {})
    # NOVO: permitir desligar envio ao Make
    send_to_make = bool(data.get("callback_to_make", True))

    try:
        result = process_video(
            video_url=video_url,
            force_language=language,
            model_size=model_size,
            extra_meta=extra_meta,
            send_to_make=send_to_make
        )
        # Retorna o resultado completo para o Make consumir diretamente
        return jsonify({"ok": True, "result": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
