#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import json
import os
import sys
import urllib.error

sys.path.insert(0, os.path.dirname(__file__))

from game_engine import (  # noqa: E402
    default_state,
    game_data,
    gemini_model,
    load_save,
    resolve_ending,
    resolve_interaction,
    save_state,
    select_scene,
    simulate,
    validate_routes,
)

ENV_FILE = "/opt/conversation-sip/.env"
PORT = int(os.environ.get("BAGGER_API_PORT", "8103"))


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


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self, limit=700000):
        length = min(int(self.headers.get("Content-Length", "0")), limit)
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _debug_enabled(self):
        return os.environ.get("BAGGER_DEBUG") == "1" and self.client_address[0] in {"127.0.0.1", "::1"}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/health":
                self._send_json(200, {"ok": True, "model": gemini_model(), "routeErrors": validate_routes()})
                return
            if path == "/api/game-data":
                self._send_json(200, game_data())
                return
            if path.startswith("/api/save/"):
                token = path.rsplit("/", 1)[-1]
                self._send_json(200, {"ok": True, "token": token, "state": load_save(token)})
                return
            if path.startswith("/api/debug/"):
                if not self._debug_enabled():
                    self._send_json(404, {"error": "Not found"})
                    return
                if path == "/api/debug/routes":
                    self._send_json(200, {"errors": validate_routes(), "data": game_data()["routes"]})
                    return
                if path.startswith("/api/debug/state/"):
                    token = path.rsplit("/", 1)[-1]
                    self._send_json(200, {"ok": True, "token": token, "state": load_save(token)})
                    return
            self._send_json(404, {"error": "Not found"})
        except FileNotFoundError:
            self._send_json(404, {"error": "Save not found"})
        except Exception as error:
            self._send_json(500, {"error": str(error)})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            payload = self._read_json()
            if path == "/api/interact":
                self._send_json(200, resolve_interaction(payload))
                return
            if path == "/api/new-game":
                self._send_json(200, {"ok": True, "state": default_state(payload.get("player"))})
                return
            if path == "/api/save":
                token = save_state(payload.get("state") or {}, payload.get("token"))
                self._send_json(200, {"ok": True, "token": token})
                return
            if path == "/api/restore":
                token = str(payload.get("token", ""))
                self._send_json(200, {"ok": True, "token": token, "state": load_save(token)})
                return
            if path.startswith("/api/debug/"):
                if not self._debug_enabled():
                    self._send_json(404, {"error": "Not found"})
                    return
                if path == "/api/debug/simulate":
                    self._send_json(200, simulate(payload.get("route", "aurora"), payload.get("strategy", "romance"), int(payload.get("steps", 80))))
                    return
                if path == "/api/debug/resolve-ending":
                    state = payload.get("state") or {}
                    route = payload.get("route", state.get("currentRoute", "aurora"))
                    self._send_json(200, {"ending": resolve_ending(state, route)})
                    return
                if path == "/api/debug/explain-scene":
                    state = payload.get("state") or default_state()
                    route = payload.get("route", state.get("currentRoute", "aurora"))
                    state["currentRoute"] = route
                    node, event, rejected = select_scene(state, {"type": payload.get("intent", "free"), "route": route})
                    self._send_json(200, {"selected": node, "calendarEvent": event, "rejected": rejected[:50]})
                    return
            self._send_json(404, {"error": "Not found"})
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            self._send_json(502, {"error": "AI service rejected the request", "detail": detail})
        except FileNotFoundError:
            self._send_json(404, {"error": "Save not found"})
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
        except Exception as error:
            self._send_json(500, {"error": str(error)})

    def log_message(self, format, *args):
        print(format % args, flush=True)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Bagger Dating Sim API listening on http://127.0.0.1:{PORT}", flush=True)
    server.serve_forever()
