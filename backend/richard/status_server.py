#!/usr/bin/env python3
import html
import json
import os
import re
import socket
import subprocess
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SERVICE = "rickroll-sip.service"
HOST = "127.0.0.1"
PORT = int(os.environ.get("RICHARD_INFO_PORT", "8095"))

SECRET_PATTERNS = [
    re.compile(r"(auth_pass=)[^;\s]+", re.I),
    re.compile(r"(SIP_PASSWORD=)\S+", re.I),
    re.compile(r"(extension_edit_sip_password[^\n]*value=)[^\s>]+", re.I),
]


def run(command: list[str], timeout: int = 5) -> tuple[int, str]:
    try:
        result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
        return result.returncode, (result.stdout + result.stderr).strip()
    except Exception as exc:
        return 1, str(exc)


def redact(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(r"\1[redacted]", text)
    return text


def file_info(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    stat = path.stat()
    return {
        "exists": True,
        "bytes": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
    }


def systemctl_show() -> dict:
    keys = [
        "ActiveState",
        "SubState",
        "LoadState",
        "UnitFileState",
        "MainPID",
        "ExecMainPID",
        "NRestarts",
        "MemoryCurrent",
        "CPUUsageNSec",
        "ActiveEnterTimestamp",
    ]
    command = ["systemctl", "show", SERVICE]
    for key in keys:
        command.extend(["--property", key])
    code, output = run(command)
    data = {"ok": code == 0}
    for line in output.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            data[key] = value
    return data


def journal() -> list[str]:
    code, output = run(["journalctl", "-u", SERVICE, "-n", "160", "--no-pager", "--output", "short-iso"], timeout=8)
    if code != 0:
        return [redact(output)]
    return redact(output).splitlines()


def derived(log_lines: list[str]) -> dict:
    joined = "\n".join(log_lines)
    registrations = re.findall(r"9415@sip\.micropoc\.de: .*?200 OK.*", joined)
    calls = re.findall(r"Call established: ([^\n]+)", joined)
    terminations = re.findall(r"terminated \(duration: ([^)]+)\)", joined)
    rtp = re.findall(r"audio=([0-9]+/[0-9]+) \(bit/s\)", joined)
    return {
        "registered": bool(registrations),
        "last_registration": registrations[-1] if registrations else None,
        "call_count_in_log_window": len(calls),
        "last_call": calls[-1] if calls else None,
        "last_call_duration": terminations[-1] if terminations else None,
        "last_audio_bitrate": rtp[-1] if rtp else None,
        "rtp_seen": "incoming rtp" in joined.lower() or "audio tx pipeline" in joined.lower() or bool(rtp),
    }


def status() -> dict:
    logs = journal()
    svc = systemctl_show()
    code, hostname = run(["hostname"], timeout=2)
    code_uptime, uptime = run(["uptime", "-p"], timeout=2)
    code_ps, ps = run(["systemctl", "status", SERVICE, "--no-pager"], timeout=5)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "host": hostname if code == 0 else socket.gethostname(),
        "host_uptime": uptime if code_uptime == 0 else None,
        "extension": "9415",
        "name": "richard-sip",
        "sip_server": "sip.micropoc.de",
        "public_site": "https://richard.gulasch.site",
        "service": svc,
        "derived": derived(logs),
        "files": {
            "mp3": file_info(ROOT / "rickroll.mp3"),
            "wav": file_info(ROOT / "rickroll.wav"),
            "received_audio": file_info(ROOT / "incoming.wav"),
            "config": file_info(ROOT / "baresip-runtime" / "config"),
        },
        "systemctl_status": redact(ps),
        "logs": logs,
    }


def render_page(data: dict) -> bytes:
    svc = data["service"]
    derived_info = data["derived"]
    active = svc.get("ActiveState") == "active"
    registered = derived_info.get("registered")
    badge_class = "ok" if active and registered else "bad"
    cards = [
        ("Service", f"{svc.get('ActiveState', '?')} / {svc.get('SubState', '?')}"),
        ("Enabled", svc.get("UnitFileState", "?")),
        ("SIP Registration", "registered" if registered else "not seen"),
        ("Extension", f"{data['extension']} ({data['name']})"),
        ("SIP Server", data["sip_server"]),
        ("Main PID", svc.get("MainPID", "?")),
        ("Restarts", svc.get("NRestarts", "?")),
        ("Last Call", derived_info.get("last_call") or "none in log window"),
        ("Last Duration", derived_info.get("last_call_duration") or "n/a"),
        ("Last Audio Bitrate", derived_info.get("last_audio_bitrate") or "n/a"),
        ("Host Uptime", data.get("host_uptime") or "n/a"),
        ("Generated", data["generated_at"]),
    ]
    card_html = "".join(
        f"<section class='card'><div class='label'>{html.escape(label)}</div><div class='value'>{html.escape(str(value))}</div></section>"
        for label, value in cards
    )
    file_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{'yes' if info.get('exists') else 'no'}</td><td>{html.escape(str(info.get('bytes', '')))}</td><td>{html.escape(str(info.get('modified', '')))}</td></tr>"
        for name, info in data["files"].items()
    )
    logs = html.escape("\n".join(data["logs"][-120:]))
    systemctl_status = html.escape(data["systemctl_status"])
    body = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="10">
<title>Richard SIP Bot</title>
<style>
:root {{ color-scheme: dark; --bg:#101014; --panel:#181822; --text:#f3f0e8; --muted:#aaa6bb; --ok:#44d17a; --bad:#ff6b6b; --line:#2a2935; }}
body {{ margin:0; font:16px/1.45 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:radial-gradient(circle at top left,#30213d,var(--bg) 40%); color:var(--text); }}
main {{ max-width:1200px; margin:0 auto; padding:32px 18px 48px; }}
h1 {{ font-size:clamp(2rem, 7vw, 5rem); line-height:.9; margin:0 0 12px; letter-spacing:-0.06em; }}
.hero {{ display:flex; gap:16px; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; margin-bottom:24px; }}
.badge {{ display:inline-flex; align-items:center; gap:8px; padding:10px 14px; border-radius:999px; background:var(--panel); border:1px solid var(--line); font-weight:700; }}
.badge::before {{ content:""; width:10px; height:10px; border-radius:50%; background:var(--bad); box-shadow:0 0 18px var(--bad); }}
.badge.ok::before {{ background:var(--ok); box-shadow:0 0 18px var(--ok); }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px; }}
.card, .panel {{ background:rgba(24,24,34,.88); border:1px solid var(--line); border-radius:18px; box-shadow:0 18px 50px rgba(0,0,0,.22); }}
.card {{ padding:16px; min-height:88px; }}
.label {{ color:var(--muted); font-size:.78rem; text-transform:uppercase; letter-spacing:.08em; }}
.value {{ margin-top:8px; overflow-wrap:anywhere; font-size:1.08rem; }}
.panel {{ margin-top:18px; padding:18px; }}
table {{ width:100%; border-collapse:collapse; }}
td, th {{ padding:10px; border-bottom:1px solid var(--line); text-align:left; }}
pre {{ overflow:auto; white-space:pre-wrap; word-break:break-word; background:#0b0b10; border:1px solid var(--line); border-radius:14px; padding:14px; max-height:520px; }}
a {{ color:#9ed0ff; }}
</style>
</head>
<body><main>
<div class="hero"><div><h1>Richard SIP Bot</h1><p>Live public status for extension 9415. Refreshes every 10 seconds.</p></div><div class="badge {badge_class}">{'online' if active and registered else 'attention needed'}</div></div>
<div class="grid">{card_html}</div>
<section class="panel"><h2>Files</h2><table><thead><tr><th>File</th><th>Exists</th><th>Bytes</th><th>Modified UTC</th></tr></thead><tbody>{file_rows}</tbody></table></section>
<section class="panel"><h2>systemctl status</h2><pre>{systemctl_status}</pre></section>
<section class="panel"><h2>journalctl -u {SERVICE}</h2><pre>{logs}</pre></section>
<section class="panel"><h2>Machine JSON</h2><p><a href="/status.json">/status.json</a></p></section>
</main></body></html>"""
    return body.encode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in ("/", "/status.json"):
            self.send_error(404)
            return
        data = status()
        if self.path == "/status.json":
            body = json.dumps(data, indent=2).encode()
            content_type = "application/json; charset=utf-8"
        else:
            body = render_page(data)
            content_type = "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        print(f"{self.address_string()} - {format % args}", flush=True)


if __name__ == "__main__":
    print(f"Serving Richard info page on http://{HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
