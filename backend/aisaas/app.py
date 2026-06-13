#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import urllib.error
import urllib.request


ENV_FILE = "/opt/conversation-sip/.env"
PORT = int(os.environ.get("AISAAS_PORT", "8101"))


def load_env_file(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file(ENV_FILE)


def gemini_model():
    model = os.environ.get("GEMINI_TEXT_MODEL") or os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"
    if "live" in model:
        return "gemini-2.5-flash"
    return model


def ask_gemini(message, context):
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("Gemini key is missing")

    prompt = f"""You are ScoutBot, a high-energy B2B sales assistant.
Sound vivid, playful, impatient, and bold, but always professional and useful.
Keep answers short. Use plain English. No technical jargon. Avoid violent, disturbing, abusive, or medicalized language.
Help users find better sales leads, improve targeting, and write outreach that is bold without being abusive.
If the user asks for a notification, return exactly the requested format and no extra intro.

Current app context:
{context[:3000]}

User question:
{message[:2000]}
"""
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.62,
            "maxOutputTokens": 420,
        },
    }).encode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model()}:generateContent?key={api_key}"
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=25) as response:
        data = json.loads(response.read().decode("utf-8"))

    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts).strip()
    text = text.replace("**", "")
    if text and text[-1] not in ".!?":
        last_word = text.rsplit(" ", 1)[-1].lower()
        if last_word in {"they", "that", "who"}:
            text = f"{text} are already showing urgency."
        else:
            text = f"{text}; prioritize accounts with obvious urgency."
    return text or "I could not generate a useful reply. Try asking in a simpler way."


def fallback_reply(message):
    if "notification" in message.lower():
        return "Pipeline alert\nHot lead pattern\nNorthstar Ledger is lighting up multiple buying signals at once."
    return "Move fast on the highest-fit account: lead with the specific buying signal and ask for a short next step."


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/health":
            self._send_json(200, {"ok": True})
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/api/chat":
            self._send_json(404, {"error": "Not found"})
            return

        length = min(int(self.headers.get("Content-Length", "0")), 20000)
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            message = str(payload.get("message", "")).strip()
            context = str(payload.get("context", ""))
            if not message:
                self._send_json(400, {"error": "Message is required"})
                return
            self._send_json(200, {"reply": ask_gemini(message, context)})
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            if error.code == 429:
                self._send_json(200, {"reply": fallback_reply(message), "fallback": True})
                return
            self._send_json(502, {"error": "AI service rejected the request", "detail": detail})
        except Exception as error:
            self._send_json(500, {"error": str(error)})

    def log_message(self, format, *args):
        print(format % args, flush=True)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"SignalScout API listening on http://127.0.0.1:{PORT}", flush=True)
    server.serve_forever()
