import os, base64, json, hmac, hashlib, sys
import requests
import yt_dlp

def hmac_sign(secret: str, payload: dict) -> str:
    if not secret:
        return ""
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return "sha256=" + sig

def write_cookies_if_any(b64: str) -> str | None:
    if not b64:
        return None
    path = "cookies.txt"
    with open(path, "wb") as f:
        f.write(base64.b64decode(b64))
    return path

def main():
    video_url = os.getenv("VIDEO_URL", "").strip()
    callback_url = os.getenv("CALLBACK_URL", "").strip()
    secret = os.getenv("CALLBACK_SECRET", "").strip()
    cookies_b64 = os.getenv("YTDLP_COOKIES_B64", "").strip()

    if not video_url:
        print("VIDEO_URL ausente", file=sys.stderr)
        sys.exit(2)

    cookiefile = write_cookies_if_any(cookies_b64)

    ydl_opts = {
        "format": "bestaudio",
        "quiet": True,
        "nocheckcertificate": True,
    }
    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile

    result = {"ok": False, "video_url": video_url}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            if "url" in info:
                audio_url = info["url"]
            elif "formats" in info and info["formats"]:
                audio_formats = [f for f in info["formats"] if f.get("acodec") not in (None, "none")]
                audio_url = (audio_formats[-1] if audio_formats else info["formats"][-1]).get("url")
            else:
                raise RuntimeError("Não foi possível obter URL de áudio.")

            result.update({
                "ok": True,
                "audio_url": audio_url,
                "title": info.get("title"),
                "id": info.get("id"),
                "ext": info.get("ext"),
                "acodec": info.get("acodec"),
                "note": "URL temporária (expira em poucas horas). Use imediatamente."
            })
    except Exception as e:
        result.update({"error": str(e)})

    print(json.dumps(result, ensure_ascii=False))

    if callback_url:
        headers = {"Content-Type": "application/json"}
        sig = hmac_sign(secret, result)
        if sig:
            headers["X-Signature"] = sig
        try:
            requests.post(callback_url, headers=headers, data=json.dumps(result, ensure_ascii=False), timeout=30)
        except Exception as e:
            print(f"Falha ao enviar callback: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
