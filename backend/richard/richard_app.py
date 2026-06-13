#!/usr/bin/env python3
import html
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "baresip-runtime"
WAV_PATH = ROOT / "rickroll.wav"
HOST = "127.0.0.1"
PORT = int(os.environ.get("RICHARD_INFO_PORT", "8095"))
LOG_LIMIT = 500

log_lock = threading.Lock()
log_lines: list[str] = []
baresip_process: subprocess.Popen | None = None
stopping = threading.Event()

SECRET_PATTERNS = [
    re.compile(r"(auth_pass=)[^;\s]+", re.I),
    re.compile(r"(SIP_PASSWORD=)\S+", re.I),
]


def redact(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(r"\1[redacted]", text)
    return text


def append_log(line: str) -> None:
    line = redact(line.rstrip())
    print(line, flush=True)
    with log_lock:
        log_lines.append(f"{datetime.now(timezone.utc).isoformat()} {line}")
        del log_lines[:-LOG_LIMIT]


def load_env(path: Path) -> dict[str, str]:
    env = dict(os.environ)
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env.setdefault(key, value)
    return env


def require(env: dict[str, str], key: str) -> str:
    value = env.get(key)
    if not value or value.startswith("fill-in-"):
        raise SystemExit(f"Missing required setting: {key}")
    return value


def run(command: list[str], timeout: int = 5) -> tuple[int, str]:
    try:
        result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
        return result.returncode, redact((result.stdout + result.stderr).strip())
    except Exception as exc:
        return 1, str(exc)


def convert_mp3(mp3_path: Path) -> None:
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(mp3_path),
            "-ac",
            "1",
            "-ar",
            "8000",
            "-acodec",
            "pcm_s16le",
            str(WAV_PATH),
        ],
        check=True,
    )


def write_baresip_config(env: dict[str, str]) -> None:
    server = require(env, "SIP_SERVER")
    username = require(env, "SIP_USERNAME")
    password = require(env, "SIP_PASSWORD")
    transport = env.get("SIP_TRANSPORT", "tcp")

    CONFIG_DIR.mkdir(exist_ok=True)
    (CONFIG_DIR / "config").write_text(
        "\n".join(
            [
                "poll_method\tepoll",
                "sip_cafile\t/etc/ssl/certs/ca-certificates.crt",
                "call_local_timeout\t120",
                "call_max_calls\t1",
                "audio_source\taufile," + str(WAV_PATH),
                "audio_player\taufile," + str(ROOT / "incoming.wav"),
                "audio_alert\taufile," + str(ROOT / "alert.wav"),
                "ausrc_srate\t8000",
                "auplay_srate\t8000",
                "ausrc_channels\t1",
                "auplay_channels\t1",
                "audio_txmode\tthread",
                "audio_buffer\t20-160",
                "rtp_ports\t12000-12100",
                "module_path\t/usr/lib/baresip/modules",
                "module\tg711.so",
                "module\taufile.so",
                "module_tmp\tuuid.so",
                "module_tmp\taccount.so",
                "module_app\tmenu.so",
                "sip_autoanswer_beep\tno",
                "",
            ]
        )
    )
    account = (
        f"<sip:{username}@{server};transport={transport}>"
        f";auth_user={username};auth_pass={password};answermode=auto"
        ";audio_codecs=PCMA,PCMU"
        f";audio_source=aufile,{WAV_PATH}"
        f";audio_player=aufile,{ROOT / 'incoming.wav'}"
    )
    (CONFIG_DIR / "accounts").write_text(account + "\n")
    (CONFIG_DIR / "contacts").write_text("\n")


def stream_baresip_output(process: subprocess.Popen) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        append_log(line)


def start_baresip() -> subprocess.Popen:
    process = subprocess.Popen(
        ["baresip", "-4", "-f", str(CONFIG_DIR), "-v"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )
    threading.Thread(target=stream_baresip_output, args=(process,), daemon=True).start()
    return process


def supervise_baresip() -> None:
    global baresip_process
    delay = 1
    while not stopping.is_set():
        baresip_process = start_baresip()
        code = baresip_process.wait()
        if stopping.is_set():
            break
        append_log(f"baresip exited with {code}; restarting in {delay}s")
        time.sleep(delay)
        delay = min(delay * 2, 30)


def file_info(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    stat = path.stat()
    return {
        "exists": True,
        "bytes": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
    }


def derived(lines: list[str]) -> dict:
    joined = "\n".join(lines)
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
    with log_lock:
        lines = list(log_lines)
    code_journal, journal_text = run(["journalctl", "-u", "rickroll-sip.service", "-n", "220", "--no-pager", "--output", "short-iso"], timeout=8)
    journal_lines = journal_text.splitlines() if code_journal == 0 else [journal_text]
    combined_lines = journal_lines + lines
    process = baresip_process
    code, hostname = run(["hostname"], timeout=2)
    code_uptime, uptime = run(["uptime", "-p"], timeout=2)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "host": hostname if code == 0 else socket.gethostname(),
        "host_uptime": uptime if code_uptime == 0 else None,
        "extension": "9415",
        "name": "richard-sip",
        "sip_server": "sip.micropoc.de",
        "public_site": "https://richard.gulasch.site",
        "service": {
            "process": "integrated python app",
            "pid": os.getpid(),
            "baresip_pid": process.pid if process else None,
            "baresip_running": process is not None and process.poll() is None,
        },
        "derived": derived(combined_lines),
        "files": {
            "mp3": file_info(ROOT / "rickroll.mp3"),
            "wav": file_info(ROOT / "rickroll.wav"),
            "received_audio": file_info(ROOT / "incoming.wav"),
            "config": file_info(ROOT / "baresip-runtime" / "config"),
        },
        "logs": lines,
        "systemd_logs": journal_lines,
    }


def render_page(data: dict) -> bytes:
    service = data["service"]
    derived_info = data["derived"]
    online = service.get("baresip_running") and derived_info.get("registered")
    cards = [
        ("App", "integrated Python app"),
        ("SIP Process", "running" if service.get("baresip_running") else "stopped"),
        ("SIP Registration", "registered" if derived_info.get("registered") else "not seen"),
        ("Extension", f"{data['extension']} ({data['name']})"),
        ("SIP Server", data["sip_server"]),
        ("App PID", service.get("pid")),
        ("baresip PID", service.get("baresip_pid")),
        ("Last Call", derived_info.get("last_call") or "none in log window"),
        ("Last Duration", derived_info.get("last_call_duration") or "n/a"),
        ("Last Audio Bitrate", derived_info.get("last_audio_bitrate") or "n/a"),
        ("RTP Seen", "yes" if derived_info.get("rtp_seen") else "no"),
        ("Generated", data["generated_at"]),
    ]
    card_html = "".join(
        f"<section class='card'><div class='label'>{html.escape(str(label))}</div><div class='value'>{html.escape(str(value))}</div></section>"
        for label, value in cards
    )
    file_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{'yes' if info.get('exists') else 'no'}</td><td>{html.escape(str(info.get('bytes', '')))}</td><td>{html.escape(str(info.get('modified', '')))}</td></tr>"
        for name, info in data["files"].items()
    )
    logs = html.escape("\n".join(data["logs"][-160:]))
    systemd_logs = html.escape("\n".join(data["systemd_logs"][-180:]))
    badge_class = "ok" if online else "bad"
    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="refresh" content="10"><title>Richard SIP Bot</title>
<style>
:root {{ color-scheme: dark; --bg:#101014; --panel:#181822; --text:#f3f0e8; --muted:#aaa6bb; --ok:#44d17a; --bad:#ff6b6b; --line:#2a2935; }}
body {{ margin:0; font:16px/1.45 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:radial-gradient(circle at top left,#30213d,var(--bg) 40%); color:var(--text); }}
main {{ max-width:1200px; margin:0 auto; padding:32px 18px 48px; }}
h1 {{ font-size:clamp(2rem, 7vw, 5rem); line-height:.9; margin:0 0 12px; letter-spacing:-0.06em; }}
.hero {{ display:flex; gap:16px; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; margin-bottom:24px; }}
.badge {{ display:inline-flex; align-items:center; gap:8px; padding:10px 14px; border-radius:999px; background:var(--panel); border:1px solid var(--line); font-weight:700; }}
.badge::before {{ content:""; width:10px; height:10px; border-radius:50%; background:var(--bad); box-shadow:0 0 18px var(--bad); }} .badge.ok::before {{ background:var(--ok); box-shadow:0 0 18px var(--ok); }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px; }} .card,.panel {{ background:rgba(24,24,34,.88); border:1px solid var(--line); border-radius:18px; box-shadow:0 18px 50px rgba(0,0,0,.22); }} .card {{ padding:16px; min-height:88px; }}
.label {{ color:var(--muted); font-size:.78rem; text-transform:uppercase; letter-spacing:.08em; }} .value {{ margin-top:8px; overflow-wrap:anywhere; font-size:1.08rem; }} .panel {{ margin-top:18px; padding:18px; }}
table {{ width:100%; border-collapse:collapse; }} td, th {{ padding:10px; border-bottom:1px solid var(--line); text-align:left; }} pre {{ overflow:auto; white-space:pre-wrap; word-break:break-word; background:#0b0b10; border:1px solid var(--line); border-radius:14px; padding:14px; max-height:620px; }} a {{ color:#9ed0ff; }}
</style></head><body><main>
<div class="hero"><div><h1>Richard SIP Bot</h1><p>Integrated Python app: SIP supervision and public live status in one process. Refreshes every 10 seconds.</p></div><div class="badge {badge_class}">{'online' if online else 'attention needed'}</div></div>
<div class="grid">{card_html}</div>
<section class="panel"><h2>Files</h2><table><thead><tr><th>File</th><th>Exists</th><th>Bytes</th><th>Modified UTC</th></tr></thead><tbody>{file_rows}</tbody></table></section>
<section class="panel"><h2>Integrated App Logs</h2><pre>{logs}</pre></section>
<section class="panel"><h2>systemd journal</h2><pre>{systemd_logs}</pre></section>
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
        append_log(f"{self.address_string()} - {format % args}")


def handle_signal(signum, frame) -> None:
    stopping.set()
    process = baresip_process
    if process and process.poll() is None:
        process.terminate()


def main() -> int:
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    env = load_env(ROOT / ".env")
    mp3_path = Path(require(env, "RICKROLL_MP3")).expanduser().resolve()
    if not mp3_path.exists():
        raise SystemExit(f"MP3 file does not exist: {mp3_path}")
    convert_mp3(mp3_path)
    write_baresip_config(env)
    threading.Thread(target=supervise_baresip, daemon=True).start()
    append_log(f"Serving Richard integrated app on http://{HOST}:{PORT}")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.timeout = 1
    while not stopping.is_set():
        server.handle_request()
    server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
