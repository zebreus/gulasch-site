#!/usr/bin/env python3
import asyncio
import html
import json
import os
import queue
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import wave
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover - status page reports this clearly.
    genai = None
    types = None


ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "baresip-runtime"
HOST = "127.0.0.1"
PORT = int(os.environ.get("INFO_PORT", "8096"))
APP_TITLE = os.environ.get("APP_TITLE", "Conversation Demo SIP Bot")
APP_NAME = os.environ.get("APP_NAME", "conversation-demo")
EXTENSION = os.environ.get("SIP_USERNAME", "9762")
SIP_SERVER = os.environ.get("SIP_SERVER", "sip.micropoc.de")
PUBLIC_SITE = os.environ.get("PUBLIC_SITE", "https://conversation.gulasch.site")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "conversation-sip.service")
RTP_PORTS = os.environ.get("RTP_PORTS", "12400-12500")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-live-preview")
GEMINI_LANGUAGE_CODE = "de-DE"
GEMINI_TURN_MODE = "local_utterance_stream_end"
LOG_LIMIT = 700
EVENT_LIMIT = 300

# ALSA loopback routing. Baresip plays caller audio to device 0,0; Python reads
# it from paired capture device 1,0. Python writes AI audio to playback 1,1;
# baresip captures it from paired capture device 0,1 and sends it to the caller.
SIP_INPUT_CAPTURE = os.environ.get("SIP_INPUT_CAPTURE", "hw:Loopback,1,0")
SIP_OUTPUT_PLAYBACK = os.environ.get("SIP_OUTPUT_PLAYBACK", "hw:Loopback,1,1")
BARESIP_AUDIO_PLAYER = os.environ.get("BARESIP_AUDIO_PLAYER", "hw:Loopback,0,0")
BARESIP_AUDIO_SOURCE = os.environ.get("BARESIP_AUDIO_SOURCE", "hw:Loopback,0,1")

INPUT_CHUNK_BYTES_16K = 3200  # 100 ms of signed 16-bit mono PCM at 16 kHz.
CALL_SILENCE_TIMEOUT = 1.25
BARGE_IN_RMS_THRESHOLD = int(os.environ.get("BARGE_IN_RMS_THRESHOLD", "550"))
VAD_RMS_THRESHOLD = int(os.environ.get("VAD_RMS_THRESHOLD", "500"))
VAD_SILENCE_DEBOUNCE = float(os.environ.get("VAD_SILENCE_DEBOUNCE", "0.4"))
VAD_HOLD_CHUNKS = int(os.environ.get("VAD_HOLD_CHUNKS", "3"))
VAD_MIN_SPEECH_CHUNKS = int(os.environ.get("VAD_MIN_SPEECH_CHUNKS", "2"))
VAD_PREROLL_CHUNKS = int(os.environ.get("VAD_PREROLL_CHUNKS", "2"))
VAD_MAX_TURN_SECONDS = float(os.environ.get("VAD_MAX_TURN_SECONDS", "8.0"))
GEMINI_GENERATION_TIMEOUT_SECONDS = float(os.environ.get("GEMINI_GENERATION_TIMEOUT_SECONDS", "12.0"))
GEMINI_NO_AUDIO_TIMEOUT_SECONDS = float(os.environ.get("GEMINI_NO_AUDIO_TIMEOUT_SECONDS", "5.0"))

RECORDINGS_DIR = ROOT / "recordings"
RECORDINGS_RETENTION = int(os.environ.get("RECORDINGS_RETENTION", "20"))
RECORDING_CALLER_RATE = 16000
RECORDING_AGENT_RATE = 24000
RECORDING_MERGE_RATE = 8000
WAV_ANALYSIS_MAX_SECONDS = 30
OUTBOUND_TARGET_MAX = int(os.environ.get("OUTBOUND_TARGET_MAX", "120"))
OUTBOUND_TTS_TEXT_MAX = int(os.environ.get("OUTBOUND_TTS_TEXT_MAX", "700"))

log_lock = threading.Lock()
log_lines: list[str] = []
baresip_process: subprocess.Popen | None = None
baresip_command_lock = threading.Lock()
stopping = threading.Event()
active_bridge: "ConversationBridge | None" = None
outbound_lock = threading.RLock()
pending_outbound_call: dict[str, Any] | None = None

SECRET_PATTERNS = [
    re.compile(r"(auth_pass=)[^;\s]+", re.I),
    re.compile(r"(SIP_PASSWORD=)\S+", re.I),
    re.compile(r"(GEMINI_API_KEY=)\S+", re.I),
    re.compile(r"(x-goog-api-key[:=]\s*)\S+", re.I),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def redact(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(r"\1[redacted]", text)
    return text


def append_log(line: str) -> None:
    line = redact(line.rstrip())
    print(line, flush=True)
    with log_lock:
        log_lines.append(f"{utc_now()} {line}")
        del log_lines[:-LOG_LIMIT]


class ConversationState:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.data: dict[str, Any] = {
            "service": {
                "state": "starting",
                "pid": os.getpid(),
                "started_at": utc_now(),
                "last_error": None,
            },
            "sip": {
                "state": "initializing",
                "registered": False,
                "baresip_running": False,
                "baresip_pid": None,
                "last_registration": None,
                "last_call": None,
                "last_call_started_at": None,
                "last_call_ended_at": None,
                "last_call_duration": None,
                "rtp_seen": False,
                "last_audio_bitrate": None,
            },
            "gemini": {
                "state": "not_configured",
                "model": GEMINI_MODEL,
                "connected": False,
                "last_event": None,
                "last_error": None,
                "reconnects": 0,
                "generation_complete_count": 0,
                "session_handle_seen": False,
                "input_transcript": "",
                "output_transcript": "",
                "vad_turns": 0,
                "audio_chunks_sent": 0,
                "audio_chunks_dropped": 0,
                "vad_mode": GEMINI_TURN_MODE,
                "language_code": GEMINI_LANGUAGE_CODE,
                "first_audio_latency_ms": None,
            },
            "audio": {
                "state": "not_started",
                "caller_audio_active": False,
                "assistant_audio_active": False,
                "barge_in_count": 0,
                "input_chunks": 0,
                "output_chunks": 0,
                "input_queue_depth": 0,
                "output_queue_depth": 0,
                "last_input_rms": 0,
                "last_error": None,
            },
            "conversation": {
                "state": "idle",
                "call_id": None,
                "turn": "idle",
                "started_at": None,
                "ended_at": None,
                "last_user_activity_at": None,
                "last_assistant_activity_at": None,
                "interruptions": 0,
            },
            "outbound": {
                "state": "idle",
                "last_target": None,
                "last_requested_at": None,
                "last_connected_at": None,
                "last_completed_at": None,
                "last_duration": None,
                "last_error": None,
                "last_tts_preview": None,
            },
            "events": [],
        }

    def update(self, section: str, **values: Any) -> None:
        with self.lock:
            self.data[section].update(values)

    def event(self, kind: str, message: str, **fields: Any) -> None:
        clean_message = redact(message)
        item = {"at": utc_now(), "kind": kind, "message": clean_message, **fields}
        with self.lock:
            self.data["events"].append(item)
            del self.data["events"][:-EVENT_LIMIT]
            if kind == "error":
                self.data["service"]["last_error"] = clean_message
        append_log(f"[{kind}] {clean_message}")

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return json.loads(json.dumps(self.data))


STATE = ConversationState()


def load_env(path: Path) -> dict[str, str]:
    env = dict(os.environ)
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env.setdefault(key, value.strip("'\""))
    return env


ENV = load_env(ROOT / ".env")


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


def has_command(name: str) -> bool:
    return shutil.which(name) is not None


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
                "audio_source\talsa," + BARESIP_AUDIO_SOURCE,
                "audio_player\talsa," + BARESIP_AUDIO_PLAYER,
                "audio_alert\talsa," + BARESIP_AUDIO_PLAYER,
                "ausrc_srate\t8000",
                "auplay_srate\t8000",
                "ausrc_channels\t1",
                "auplay_channels\t1",
                "audio_txmode\tthread",
                "audio_buffer\t20-160",
                "rtp_ports\t" + RTP_PORTS,
                "module_path\t/usr/lib/baresip/modules",
                "module\tg711.so",
                "module\talsa.so",
                "module_tmp\tuuid.so",
                "module_tmp\taccount.so",
                "module_app\tstdio.so",
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
        f";audio_source=alsa,{BARESIP_AUDIO_SOURCE}"
        f";audio_player=alsa,{BARESIP_AUDIO_PLAYER}"
    )
    (CONFIG_DIR / "accounts").write_text(account + "\n")
    (CONFIG_DIR / "contacts").write_text("\n")
    STATE.update("sip", state="config_written")
    STATE.event("sip", "baresip runtime config written for realtime ALSA loopback")


def pcm16_rms(data: bytes) -> int:
    if len(data) < 2:
        return 0
    total = 0
    count = len(data) // 2
    for i in range(0, len(data) - 1, 2):
        sample = int.from_bytes(data[i : i + 2], "little", signed=True)
        total += sample * sample
    return int((total / max(count, 1)) ** 0.5)


class WavWriter:
    def __init__(self, path: Path, sample_rate: int) -> None:
        self.path = path
        self.sample_rate = sample_rate
        self.lock = threading.Lock()
        self._file: wave.Wave_write | None = None
        self.bytes_written = 0
        self.error: str | None = None
        self._open()

    def _open(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handle = wave.open(str(self.path), "wb")
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(self.sample_rate)
            self._file = handle
        except Exception as exc:  # pragma: no cover - surfaced via status payload
            self.error = redact(str(exc))
            append_log(f"recording open failed for {self.path}: {self.error}")

    def write(self, pcm: bytes) -> None:
        if not pcm or self._file is None:
            return
        with self.lock:
            if self._file is None:
                return
            try:
                self._file.writeframesraw(pcm)
                self.bytes_written += len(pcm)
            except Exception as exc:
                self.error = redact(str(exc))
                self._close_unlocked()

    def write_silence(self, byte_count: int) -> None:
        byte_count -= byte_count % 2
        if byte_count <= 0 or self._file is None:
            return
        block = b"\x00\x00" * self.sample_rate
        with self.lock:
            if self._file is None:
                return
            remaining = byte_count
            try:
                while remaining > 0:
                    chunk = block[: min(len(block), remaining)]
                    self._file.writeframesraw(chunk)
                    self.bytes_written += len(chunk)
                    remaining -= len(chunk)
            except Exception as exc:
                self.error = redact(str(exc))
                self._close_unlocked()

    def close(self) -> int:
        with self.lock:
            self._close_unlocked()
        return self.bytes_written

    def byte_count(self) -> int:
        with self.lock:
            return self.bytes_written

    def _close_unlocked(self) -> None:
        if self._file is None:
            return
        try:
            self._file.close()
        except Exception as exc:
            self.error = redact(str(exc))
        finally:
            self._file = None


def merge_recordings(call_id: str, caller_path: Path, agent_path: Path, merged_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"call_id": call_id, "merged": False}
    if not caller_path.exists() or not agent_path.exists():
        result["reason"] = "source file missing"
        return result
    if caller_path.stat().st_size < 256 or agent_path.stat().st_size < 256:
        result["reason"] = "source too short"
        return result
    if not has_command("ffmpeg"):
        result["reason"] = "ffmpeg unavailable"
        return result
    merged_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-i",
        str(caller_path),
        "-i",
        str(agent_path),
        "-filter_complex",
        (
            f"[0:a]aresample={RECORDING_MERGE_RATE},asetpts=PTS-STARTPTS,volume=1.0[c0];"
            f"[1:a]aresample={RECORDING_MERGE_RATE},asetpts=PTS-STARTPTS,volume=1.0[c1];"
            f"[c0][c1]amix=inputs=2:duration=longest:normalize=0:dropout_transition=0,"
            f"pan=mono|c0=c0,aresample={RECORDING_MERGE_RATE}"
        ),
        "-ac",
        "1",
        "-ar",
        str(RECORDING_MERGE_RATE),
        "-c:a",
        "pcm_s16le",
        str(merged_path),
    ]
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except Exception as exc:
        result["reason"] = f"ffmpeg error: {exc}"
        return result
    if proc.returncode != 0:
        result["reason"] = redact(proc.stderr.strip()[-300:] or "ffmpeg exited non-zero")
        return result
    if not merged_path.exists() or merged_path.stat().st_size < 256:
        result["reason"] = "merged file missing or empty"
        return result
    result["merged"] = True
    result["bytes"] = merged_path.stat().st_size
    return result


def recording_path(kind: str, call_id: str) -> Path:
    safe_id = re.sub(r"[^A-Za-z0-9._-]", "_", call_id)
    return RECORDINGS_DIR / f"{kind}-{safe_id}.wav"


class ConversationBridge:
    def __init__(self, call_id: str, env: dict[str, str], initial_tts_text: str | None = None) -> None:
        self.call_id = call_id
        self.env = env
        self.initial_tts_text = initial_tts_text
        self.stop_event = threading.Event()
        self.input_queue: queue.Queue[bytes] = queue.Queue(maxsize=80)
        self.output_queue: queue.Queue[bytes] = queue.Queue(maxsize=120)
        self.threads: list[threading.Thread] = []
        self.processes: list[subprocess.Popen] = []
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        self.caller_path = recording_path("caller", call_id)
        self.agent_path = recording_path("agent", call_id)
        self.merged_path = recording_path("merged", call_id)
        self.caller_writer = WavWriter(self.caller_path, RECORDING_CALLER_RATE)
        self.agent_writer = WavWriter(self.agent_path, RECORDING_AGENT_RATE)
        self.started_at = utc_now()
        self.started_monotonic = time.monotonic()
        self.ended_at: str | None = None
        self.gemini_input_queue: asyncio.Queue | None = None
        self.gemini_loop_ref: asyncio.AbstractEventLoop | None = None
        self.vad_user_speaking = False
        self.vad_last_speech_time = 0.0
        self.vad_turn_started_at = 0.0
        self.vad_silence_chunks = 0
        self.vad_speech_chunks = 0
        self.vad_turns = 0
        self.vad_preroll: deque[bytes] = deque(maxlen=VAD_PREROLL_CHUNKS)
        self.vad_audio_chunks_sent = 0
        self.audio_chunks_read = 0
        self.rms_ema = 0.0
        self.gemini_sender_dropped = 0
        self.last_local_turn_end_at = 0.0
        self.seen_audio_for_generation = False
        self.input_transcript = ""
        self.output_transcript = ""
        self.gemini_generation_done: asyncio.Event | None = None
        self.gemini_session_stop: asyncio.Event | None = None
        self.suppress_agent_output = False
        self.assistant_playing_until = 0.0
        self.response_turn_end_at = 0.0
        self.initial_greeting_sent = False
        self.initial_tts_pending = bool(initial_tts_text)
        self.initial_tts_protected_until = 0.0

    def start(self) -> None:
        STATE.update(
            "conversation",
            state="in_call",
            call_id=self.call_id,
            started_at=utc_now(),
            ended_at=None,
            turn="listening",
            interruptions=0,
        )
        STATE.update(
            "audio",
            state="starting",
            caller_audio_active=False,
            assistant_audio_active=False,
            barge_in_count=0,
            input_chunks=0,
            output_chunks=0,
            input_queue_depth=0,
            output_queue_depth=0,
            last_input_rms=0,
            last_error=None,
        )
        STATE.update(
            "gemini",
            connected=False,
            last_event=None,
            last_error=None,
            generation_complete_count=0,
            session_handle_seen=False,
            input_transcript="",
            output_transcript="",
            vad_turns=0,
            audio_chunks_sent=0,
            audio_chunks_dropped=0,
            first_audio_latency_ms=None,
        )
        bridge_mode = "outbound TTS" if self.initial_tts_text else "realtime Gemini"
        STATE.event("conversation", f"starting {bridge_mode} bridge for call {self.call_id}")
        for target, name in [
            (self.capture_loop, "sip-audio-capture"),
            (self.playback_loop, "sip-audio-playback"),
            (self.gemini_loop, "gemini-live"),
        ]:
            thread = threading.Thread(target=target, name=name, daemon=True)
            self.threads.append(thread)
            thread.start()

    def stop(self) -> None:
        if self.stop_event.is_set():
            return
        self.stop_event.set()
        STATE.event("conversation", f"stopping realtime bridge for call {self.call_id}")
        for process in list(self.processes):
            if process.poll() is None:
                process.terminate()
        self.pad_agent_recording_to_now()
        caller_bytes = self.caller_writer.close()
        agent_bytes = self.agent_writer.close()
        self.ended_at = utc_now()
        STATE.update(
            "conversation",
            state="ended",
            ended_at=self.ended_at,
            turn="idle",
            call_id=None,
        )
        STATE.update("audio", state="stopped", caller_audio_active=False, assistant_audio_active=False)
        STATE.update("gemini", connected=False, state="disconnected")
        threading.Thread(target=self._finalize_recording, args=(caller_bytes, agent_bytes), daemon=True).start()

    def _finalize_recording(self, caller_bytes: int, agent_bytes: int) -> None:
        result = merge_recordings(self.call_id, self.caller_path, self.agent_path, self.merged_path)
        record = {
            "call_id": self.call_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at or utc_now(),
            "caller": wav_info(self.caller_path, caller_bytes),
            "agent": wav_info(self.agent_path, agent_bytes),
            "merged": wav_info(self.merged_path, result.get("bytes", 0) if result.get("merged") else 0),
            "merge": result,
        }
        with recordings_lock:
            RECORDINGS.append(record)
            if len(RECORDINGS) > RECORDINGS_RETENTION:
                stale = RECORDINGS[:-RECORDINGS_RETENTION]
                del RECORDINGS[:-RECORDINGS_RETENTION]
                for old in stale:
                    for path in (old.get("caller", {}).get("path"), old.get("agent", {}).get("path"), old.get("merged", {}).get("path")):
                        if path:
                            try:
                                Path(path).unlink(missing_ok=True)
                            except OSError:
                                pass
        if result.get("merged"):
            STATE.event("recording", f"recording merged: {self.merged_path.name} ({result.get('bytes')} bytes)")
        else:
            STATE.event("recording", f"recording merge skipped: {result.get('reason', 'unknown')}")

    def pad_agent_recording_to_now(self) -> None:
        caller_samples = self.caller_writer.byte_count() // 2
        if caller_samples:
            target_bytes = int(caller_samples * RECORDING_AGENT_RATE / RECORDING_CALLER_RATE) * 2
        else:
            elapsed = max(0.0, time.monotonic() - self.started_monotonic)
            target_bytes = int(elapsed * RECORDING_AGENT_RATE) * 2
        self.agent_writer.write_silence(target_bytes - self.agent_writer.byte_count())

    def write_agent_recording(self, pcm: bytes) -> None:
        self.pad_agent_recording_to_now()
        self.agent_writer.write(pcm)

    def capture_loop(self) -> None:
        if not has_command("ffmpeg"):
            self.fail_audio("ffmpeg is not installed")
            return
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-f",
            "alsa",
            "-ac",
            "1",
            "-ar",
            "8000",
            "-i",
            SIP_INPUT_CAPTURE,
            "-f",
            "s16le",
            "-acodec",
            "pcm_s16le",
            "-ac",
            "1",
            "-ar",
            "16000",
            "pipe:1",
        ]
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.processes.append(process)
            STATE.update("audio", state="capture_running")
            assert process.stdout is not None
            while not self.stop_event.is_set():
                chunk = process.stdout.read(INPUT_CHUNK_BYTES_16K)
                if not chunk:
                    if process.poll() is not None:
                        break
                    continue
                rms = pcm16_rms(chunk)
                caller_speaking = rms >= BARGE_IN_RMS_THRESHOLD
                vad_speaking = rms >= VAD_RMS_THRESHOLD
                initial_tts_protected = self.initial_tts_protected()
                if vad_speaking and not initial_tts_protected:
                    STATE.update("conversation", last_user_activity_at=utc_now())
                if not initial_tts_protected:
                    self.handle_barge_in(caller_speaking)
                self.put_latest(self.input_queue, chunk)
                self.caller_writer.write(chunk)
                if not initial_tts_protected:
                    self.update_vad(vad_speaking, chunk)
                self.update_rms_ema(rms, vad_speaking)
                STATE.update(
                    "audio",
                    caller_audio_active=caller_speaking and not initial_tts_protected,
                    input_chunks=STATE.snapshot()["audio"]["input_chunks"] + 1,
                    input_queue_depth=self.input_queue.qsize(),
                    last_input_rms=rms,
                )
            err = process.stderr.read().decode(errors="replace") if process.stderr else ""
            if err.strip() and not self.stop_event.is_set():
                self.fail_audio(redact(err.strip()[-500:]))
        except Exception as exc:
            self.fail_audio(str(exc))

    def playback_loop(self) -> None:
        if not has_command("sox"):
            self.fail_audio("sox is not installed")
            return
        command = [
            "sox",
            "-q",
            "-t",
            "raw",
            "-r",
            "24000",
            "-b",
            "16",
            "-e",
            "signed-integer",
            "-c",
            "1",
            "-",
            "-t",
            "alsa",
            SIP_OUTPUT_PLAYBACK,
            "rate",
            "8000",
        ]
        process = None
        last_audio_at = 0.0
        while not self.stop_event.is_set():
            try:
                chunk = self.output_queue.get(timeout=0.2)
            except queue.Empty:
                STATE.update("audio", assistant_audio_active=False, output_queue_depth=0)
                if process is not None and process.poll() is None and time.time() - last_audio_at > 1.0:
                    try:
                        process.stdin.close()
                    except Exception:
                        pass
                    try:
                        process.wait(timeout=0.5)
                    except Exception:
                        process.terminate()
                    process = None
                continue
            if process is None or process.poll() is not None:
                try:
                    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    self.processes.append(process)
                except Exception as exc:
                    self.fail_audio(f"sox restart failed: {exc}")
                    time.sleep(0.1)
                    continue
            assert process.stdin is not None
            try:
                process.stdin.write(chunk)
                process.stdin.flush()
                self.write_agent_recording(chunk)
            except (BrokenPipeError, OSError):
                # sox exited (often after long silence); outer loop will restart it
                try:
                    process.wait(timeout=0.1)
                except Exception:
                    pass
                process = None
                continue
            last_audio_at = time.time()
            STATE.update(
                "audio",
                state="playback_running",
                assistant_audio_active=True,
                output_chunks=STATE.snapshot()["audio"]["output_chunks"] + 1,
                output_queue_depth=self.output_queue.qsize(),
            )
            STATE.update("conversation", turn="assistant_speaking", last_assistant_activity_at=utc_now())

    def handle_barge_in(self, caller_speaking: bool) -> None:
        if self.initial_tts_protected():
            return
        audio = STATE.snapshot()["audio"]
        assistant_still_playing = audio.get("assistant_audio_active") or time.time() < self.assistant_playing_until
        if caller_speaking and assistant_still_playing:
            cleared = 0
            while True:
                try:
                    self.output_queue.get_nowait()
                    cleared += 1
                except queue.Empty:
                    break
            snap = STATE.snapshot()
            STATE.update(
                "audio",
                state="barge_in_detected",
                barge_in_count=snap["audio"]["barge_in_count"] + 1,
                assistant_audio_active=False,
                output_queue_depth=0,
            )
            STATE.update(
                "conversation",
                state="interrupted",
                turn="user_speaking",
                interruptions=snap["conversation"]["interruptions"] + 1,
            )
            self.suppress_agent_output = True
            self.assistant_playing_until = 0.0
            STATE.event("audio", f"barge-in detected; cleared {cleared} queued audio chunks")

    def initial_tts_protected(self) -> bool:
        return bool(self.initial_tts_text) and (
            self.initial_tts_pending or time.time() < self.initial_tts_protected_until
        )

    def update_vad(self, speaking: bool, chunk: bytes) -> None:
        now = time.time()
        if not self.vad_user_speaking:
            self.vad_preroll.append(chunk)
            if speaking:
                self.vad_speech_chunks += 1
            else:
                self.vad_speech_chunks = 0
            if self.vad_speech_chunks >= VAD_MIN_SPEECH_CHUNKS:
                self.vad_user_speaking = True
                self.vad_silence_chunks = 0
                self.vad_last_speech_time = now
                self.vad_turn_started_at = now
                self.vad_turns += 1
                self.seen_audio_for_generation = False
                STATE.update("conversation", turn="user_speaking")
                STATE.update("gemini", vad_turns=self.vad_turns)
                STATE.event("vad", f"activity_start (turn {self.vad_turns})")
                self.enqueue_gemini("start")
                for buffered_chunk in list(self.vad_preroll):
                    self.enqueue_gemini(buffered_chunk)
                self.vad_preroll.clear()
            return

        self.enqueue_gemini(chunk)
        if speaking:
            self.vad_silence_chunks = 0
            self.vad_last_speech_time = now
            return

        self.vad_silence_chunks += 1
        silence_long_enough = (
            self.vad_silence_chunks >= VAD_HOLD_CHUNKS
            and (now - self.vad_last_speech_time) >= VAD_SILENCE_DEBOUNCE
        )
        max_turn_reached = (now - self.vad_turn_started_at) >= VAD_MAX_TURN_SECONDS
        if silence_long_enough or max_turn_reached:
            self.vad_user_speaking = False
            self.vad_speech_chunks = 0
            self.last_local_turn_end_at = now
            STATE.update("conversation", turn="listening")
            reason = "max duration" if max_turn_reached and not silence_long_enough else f"{self.vad_silence_chunks} silent chunks"
            STATE.event("vad", f"activity_end after {reason}")
            self.enqueue_gemini("end")

    def update_rms_ema(self, rms: int, speaking: bool) -> None:
        self.audio_chunks_read += 1
        alpha = 0.05
        self.rms_ema = (1 - alpha) * self.rms_ema + alpha * rms
        if speaking and self.audio_chunks_read % 50 == 0:
            STATE.update("audio", input_rms_ema=int(self.rms_ema))

    def enqueue_gemini(self, item: Any) -> None:
        queue_ref = self.gemini_input_queue
        loop_ref = self.gemini_loop_ref
        if queue_ref is None or loop_ref is None:
            return
        if isinstance(item, str):
            try:
                loop_ref.call_soon_threadsafe(self._put_gemini_vad, item)
            except RuntimeError:
                pass
            return
        try:
            loop_ref.call_soon_threadsafe(self._put_gemini_audio, item)
        except RuntimeError:
            pass

    def _put_gemini_vad(self, signal: str) -> None:
        if self.gemini_input_queue is None:
            return
        try:
            self.gemini_input_queue.put_nowait(signal)
        except asyncio.QueueFull:
            STATE.event("vad", "vad signal dropped: queue full")

    def _put_gemini_audio(self, chunk: bytes) -> None:
        if self.gemini_input_queue is None:
            return
        try:
            self.gemini_input_queue.put_nowait(chunk)
        except asyncio.QueueFull:
            try:
                self.gemini_input_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                self.gemini_input_queue.put_nowait(chunk)
            except asyncio.QueueFull:
                pass

    def gemini_loop(self) -> None:
        api_key = self.env.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            STATE.update("gemini", state="not_configured", last_error="GEMINI_API_KEY missing")
            STATE.event("error", "GEMINI_API_KEY missing; cannot start Flash Live session")
            return
        if genai is None or types is None:
            STATE.update("gemini", state="dependency_missing", last_error="google-genai missing")
            STATE.event("error", "google-genai dependency is missing")
            return
        asyncio.run(self.gemini_async(api_key))

    async def gemini_async(self, api_key: str) -> None:
        client = genai.Client(api_key=api_key)
        system_instruction = self.env.get(
            "GEMINI_SYSTEM_INSTRUCTION",
            "Du bist ein knapper, freundlicher Telefonassistent. "
            "Antworte immer auf Deutsch, auch wenn die Spracherkennung eine andere Sprache vermutet. "
            "Sprich in kurzen natuerlichen Saetzen. Wenn du unterbrochen wirst, hoere sofort auf und reagiere auf die neueste Aussage des Anrufers.",
        )
        if self.initial_tts_text:
            system_instruction += (
                " Bei Outbound-TTS-Nachrichten sprich den vorgegebenen Text wortgetreu, "
                "erhalte dessen Sprache und fuege nichts hinzu, bis der Angerufene antwortet."
            )
        config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            system_instruction=system_instruction,
            speech_config=types.SpeechConfig(language_code=GEMINI_LANGUAGE_CODE),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL),
            realtime_input_config=types.RealtimeInputConfig(
                activity_handling=types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS,
                turn_coverage=types.TurnCoverage.TURN_INCLUDES_ONLY_ACTIVITY,
                automatic_activity_detection=types.AutomaticActivityDetection(
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                    silence_duration_ms=350,
                    prefix_padding_ms=100,
                ),
            ),
        )
        self.gemini_loop_ref = asyncio.get_running_loop()
        self.gemini_input_queue = asyncio.Queue(maxsize=1200)
        STATE.update(
            "gemini",
            state="ready",
            connected=False,
            model=GEMINI_MODEL,
            language_code=GEMINI_LANGUAGE_CODE,
            last_error=None,
        )
        STATE.event("gemini", f"opening continuous Live pipe ({GEMINI_MODEL}, German speech)")
        try:
            await self.gemini_pipe_loop(client, config)
        except Exception as exc:
            if not self.stop_event.is_set():
                snap = STATE.snapshot()
                STATE.update(
                    "gemini",
                    state="error",
                    connected=False,
                    last_error=redact(str(exc)),
                    reconnects=snap["gemini"].get("reconnects", 0) + 1,
                )
                STATE.event("error", f"Gemini Live pipe failed: {exc}")
        finally:
            self.gemini_input_queue = None
            self.gemini_loop_ref = None
            self.gemini_generation_done = None

    async def gemini_pipe_loop(self, client: Any, config: Any) -> None:
        queue_ref = self.gemini_input_queue
        if queue_ref is None:
            return
        backoff = 1.0
        pipe_attempt = 0
        while not self.stop_event.is_set():
            pipe_attempt += 1
            session_stop = asyncio.Event()
            self.gemini_session_stop = session_stop
            STATE.update("gemini", state="connecting", connected=False, last_event=f"pipe_attempt_{pipe_attempt}")
            try:
                async with client.aio.live.connect(model=GEMINI_MODEL, config=config) as session:
                    self.gemini_generation_done = asyncio.Event()
                    if pipe_attempt > 1:
                        snap = STATE.snapshot()
                        STATE.update("gemini", reconnects=snap["gemini"].get("reconnects", 0) + 1)
                    STATE.update(
                        "gemini",
                        state="connected",
                        connected=True,
                        last_event="setup_complete",
                    )
                    STATE.event("gemini", f"continuous Live pipe connected (attempt {pipe_attempt})")
                    backoff = 1.0
                    self.suppress_agent_output = False
                    self.seen_audio_for_generation = False

                    receiver_task = asyncio.create_task(self.pipe_receiver(session, session_stop))
                    await self.send_initial_greeting(session)
                    sender_task = asyncio.create_task(self.pipe_sender(session, queue_ref, session_stop))
                    done, pending = await asyncio.wait(
                        {sender_task, receiver_task},
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    if not session_stop.is_set():
                        STATE.event("gemini", "pipe task ended; signalling graceful stop")
                    session_stop.set()
                    for task in pending:
                        try:
                            await asyncio.wait_for(task, timeout=2.0)
                        except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                            task.cancel()
                        try:
                            await task
                        except (asyncio.CancelledError, Exception):
                            pass
                    for task in done:
                        if task.cancelled():
                            continue
                        exc = task.exception()
                        if exc and not self.stop_event.is_set():
                            STATE.event("error", f"pipe task ended: {exc}")
            except Exception as exc:
                if not self.stop_event.is_set():
                    snap = STATE.snapshot()
                    STATE.update(
                        "gemini",
                        state="error",
                        connected=False,
                        last_error=redact(str(exc)),
                        reconnects=snap["gemini"].get("reconnects", 0) + 1,
                    )
                    STATE.event("error", f"Live pipe connection failed: {exc}")
            finally:
                self.gemini_session_stop = None
            if self.stop_event.is_set():
                break
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 8.0)

    async def send_initial_greeting(self, session: Any) -> None:
        if self.initial_greeting_sent:
            return
        self.initial_greeting_sent = True
        if self.initial_tts_text:
            greeting = (
                "Speak this outbound TTS message exactly as written. Preserve the language, "
                "do not add an introduction, and then wait for the callee:\n\n"
                f"{self.initial_tts_text}"
            )
        else:
            greeting = self.env.get(
                "GEMINI_INITIAL_GREETING",
                "Begruesse den Anrufer kurz auf Deutsch und bitte ihn, nach dem Signal zu sprechen.",
            )
        try:
            self.response_turn_end_at = time.time()
            await session.send_realtime_input(text=greeting)
            STATE.update("gemini", last_event="initial_greeting_sent")
            STATE.event("gemini", "initial greeting requested")
        except Exception as exc:
            STATE.update("gemini", last_error=redact(str(exc))[:200], last_event="initial_greeting_error")
            STATE.event("error", f"initial greeting failed: {exc}")

    async def pipe_sender(self, session: Any, queue_ref: asyncio.Queue, session_stop: asyncio.Event) -> None:
        stream_started = False
        stream_ended = False
        sender_turn = self.vad_turns
        turn_chunks = 0
        while not self.stop_event.is_set() and not session_stop.is_set():
            try:
                item = await asyncio.wait_for(queue_ref.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            if isinstance(item, str):
                if item == "start":
                    sender_turn = self.vad_turns
                    turn_chunks = 0
                    stream_started = True
                    stream_ended = False
                    self.seen_audio_for_generation = False
                    STATE.update("gemini", last_event="activity_start")
                    STATE.event("gemini", f"streaming turn {sender_turn} started")
                elif item == "end" and stream_started and not stream_ended:
                    try:
                        done = self.gemini_generation_done
                        if done is not None:
                            done.clear()
                        self.response_turn_end_at = time.time()
                        await session.send_realtime_input(audio_stream_end=True)
                        STATE.update("gemini", last_event="audio_stream_end")
                        STATE.event("gemini", f"streaming turn {sender_turn} ended after {turn_chunks} chunks")
                        stream_ended = True
                    except Exception as exc:
                        STATE.update("gemini", last_error=redact(str(exc))[:200], last_event="stream_end_error")
                        STATE.event("error", f"audio_stream_end failed: {exc}")
                        session_stop.set()
                        return
                    if await self.wait_for_generation_complete():
                        session_stop.set()
                        return
                    STATE.event("gemini", "generation wait timed out; reconnecting Live pipe")
                    session_stop.set()
                    return
                continue
            if not isinstance(item, bytes):
                continue
            if not stream_started or stream_ended:
                self.gemini_sender_dropped += 1
                continue
            try:
                await session.send_realtime_input(
                    audio=types.Blob(data=item, mime_type="audio/pcm;rate=16000")
                )
            except Exception as exc:
                STATE.update("gemini", last_error=redact(str(exc))[:200], last_event="send_error")
                STATE.event("error", f"send_realtime_input failed: {exc}")
                session_stop.set()
                return
            turn_chunks += 1
            self.vad_audio_chunks_sent += 1
            STATE.update(
                "gemini",
                state="listening",
                last_event="audio_input",
                audio_chunks_sent=self.vad_audio_chunks_sent,
                audio_chunks_dropped=self.gemini_sender_dropped,
            )
        STATE.update("gemini", last_event="sender_stopped")

    async def wait_for_generation_complete(self) -> bool:
        done = self.gemini_generation_done
        if done is None:
            return False
        try:
            await asyncio.wait_for(done.wait(), timeout=GEMINI_GENERATION_TIMEOUT_SECONDS)
            return True
        except asyncio.TimeoutError:
            return False

    async def pipe_receiver(self, session: Any, session_stop: asyncio.Event) -> None:
        receive = getattr(session, "_receive", None) or session.receive
        try:
            while not self.stop_event.is_set() and not session_stop.is_set():
                message = await receive()
                server_content = getattr(message, "server_content", None)
                if server_content is None and not getattr(message, "go_away", None) and not getattr(message, "session_resumption_update", None):
                    continue
                await self.handle_gemini_message(message)
        except Exception as exc:
            STATE.update("gemini", last_error=redact(str(exc))[:200], last_event="receive_error")
            STATE.event("error", f"session._receive failed: {exc}")
            session_stop.set()
            raise

    async def gemini_sender(self, session: Any) -> None:
        queue_ref = self.gemini_input_queue
        if queue_ref is None:
            return
        stream_ended = False
        awaiting_generation = False
        generation_wait_started = 0.0
        sender_turn = 0
        turn_chunks = 0
        while not self.stop_event.is_set():
            if awaiting_generation:
                done = self.gemini_generation_done
                if done is not None and done.is_set():
                    awaiting_generation = False
                elif time.monotonic() - generation_wait_started > 8.0:
                    STATE.event("gemini", "generation wait timed out; sending next queued turn")
                    awaiting_generation = False
                else:
                    await asyncio.sleep(0.05)
                    continue
            try:
                item = await asyncio.wait_for(queue_ref.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            if isinstance(item, str):
                if item == "start":
                    sender_turn += 1
                    turn_chunks = 0
                    stream_ended = False
                    STATE.update("gemini", last_event="activity_start")
                    STATE.event("gemini", f"sending turn {sender_turn} started")
                elif item == "end":
                    if not stream_ended:
                        try:
                            done = self.gemini_generation_done
                            if done is not None:
                                done.clear()
                            await session.send_realtime_input(audio_stream_end=True)
                            STATE.update("gemini", last_event="audio_stream_end")
                            STATE.event("gemini", f"sending turn {sender_turn} ended after {turn_chunks} chunks")
                            stream_ended = True
                            awaiting_generation = True
                            generation_wait_started = time.monotonic()
                        except Exception as exc:
                            STATE.update("gemini", last_error=redact(str(exc))[:200], last_event="stream_end_error")
                continue
            if stream_ended:
                # The model closed the turn; ignore further audio until next "start".
                self.gemini_sender_dropped += 1
                continue
            await session.send_realtime_input(
                audio=types.Blob(data=item, mime_type="audio/pcm;rate=16000")
            )
            turn_chunks += 1
            self.vad_audio_chunks_sent += 1
            STATE.update(
                "gemini",
                state="listening",
                last_event="audio_input",
                audio_chunks_sent=self.vad_audio_chunks_sent,
                audio_chunks_dropped=self.gemini_sender_dropped,
            )

    async def gemini_receiver(self, session: Any) -> None:
        async for message in session.receive():
            if self.stop_event.is_set():
                break
            await self.handle_gemini_message(message)

    async def handle_gemini_message(self, message: Any) -> None:
        if getattr(message, "go_away", None):
            STATE.update("gemini", last_event="go_away")
            STATE.event("gemini", "server sent GoAway; session will reconnect on next call")
        if getattr(message, "session_resumption_update", None):
            STATE.update("gemini", session_handle_seen=True, last_event="session_resumption_update")
        server_content = getattr(message, "server_content", None)
        if server_content is None:
            return False
        if getattr(server_content, "input_transcription", None):
            text = getattr(server_content.input_transcription, "text", "") or ""
            if text:
                self.input_transcript = (self.input_transcript + " " + text).strip()
                STATE.update("gemini", input_transcript=self.input_transcript, last_event="input_transcription")
        if getattr(server_content, "output_transcription", None):
            text = getattr(server_content.output_transcription, "text", "") or ""
            if text:
                self.output_transcript = (self.output_transcript + text).strip()
                STATE.update("gemini", output_transcript=self.output_transcript, last_event="output_transcription")
        model_turn = getattr(server_content, "model_turn", None)
        parts = getattr(model_turn, "parts", None) if model_turn else None
        if parts:
            for part in parts:
                inline_data = getattr(part, "inline_data", None)
                data = getattr(inline_data, "data", None) if inline_data else None
                if data:
                    if self.suppress_agent_output:
                        STATE.update("gemini", last_event="audio_output_suppressed")
                        continue
                    if not self.seen_audio_for_generation:
                        self.seen_audio_for_generation = True
                        if self.response_turn_end_at:
                            latency_ms = int((time.time() - self.response_turn_end_at) * 1000)
                            STATE.update("gemini", first_audio_latency_ms=latency_ms)
                            STATE.event("gemini", f"first audio after local turn end: {latency_ms} ms")
                    chunk_duration = len(data) / 2 / RECORDING_AGENT_RATE
                    self.assistant_playing_until = max(time.time(), self.assistant_playing_until) + chunk_duration
                    if self.initial_tts_pending:
                        self.initial_tts_protected_until = max(
                            self.initial_tts_protected_until,
                            self.assistant_playing_until + 0.5,
                        )
                        STATE.update("outbound", state="speaking")
                    self.put_latest(self.output_queue, data)
                    STATE.update("gemini", state="responding", last_event="audio_output")
                    STATE.update("conversation", turn="assistant_speaking")
                text = getattr(part, "text", None)
                if text:
                    STATE.update("gemini", output_transcript=text, last_event="text_output")
        if getattr(server_content, "generation_complete", False):
            if self.initial_tts_pending:
                self.initial_tts_pending = False
                self.initial_tts_protected_until = max(self.initial_tts_protected_until, self.assistant_playing_until + 0.5)
                STATE.update("outbound", state="listening")
                STATE.event("outbound", "outbound TTS message finished; caller audio enabled")
            self.seen_audio_for_generation = False
            self.suppress_agent_output = False
            done = self.gemini_generation_done
            if done is not None:
                done.set()
            snap = STATE.snapshot()
            generation_count = snap["gemini"]["generation_complete_count"] + 1
            STATE.update(
                "gemini",
                state="generation_complete",
                generation_complete_count=generation_count,
                last_event="generation_complete",
            )
            STATE.event("gemini", f"generation_complete ({generation_count})")
            STATE.update("conversation", turn="listening")
        if getattr(server_content, "turn_complete", False):
            STATE.update("conversation", turn="listening")
        return bool(getattr(server_content, "generation_complete", False))

    @staticmethod
    def put_latest(target: queue.Queue[bytes], chunk: bytes) -> None:
        try:
            target.put_nowait(chunk)
        except queue.Full:
            try:
                target.get_nowait()
            except queue.Empty:
                pass
            target.put_nowait(chunk)

    @staticmethod
    def fail_audio(message: str) -> None:
        STATE.update("audio", state="error", last_error=redact(message))
        STATE.event("error", f"audio bridge error: {message}")


def start_bridge(call_label: str, outbound_request: dict[str, Any] | None = None) -> None:
    global active_bridge
    if active_bridge is not None:
        active_bridge.stop()
    call_id = f"{int(time.time())}-{abs(hash(call_label)) % 10000}"
    initial_tts_text = outbound_request.get("tts_text") if outbound_request else None
    active_bridge = ConversationBridge(call_id, ENV, initial_tts_text=initial_tts_text)
    active_bridge.start()


def stop_bridge() -> None:
    global active_bridge
    if active_bridge is not None:
        active_bridge.stop()
        active_bridge = None


def handle_baresip_line(line: str) -> None:
    lower = line.lower()
    if "200 ok" in lower and f"{EXTENSION}@{SIP_SERVER}" in line:
        STATE.update("sip", state="sip_registered", registered=True, last_registration=line)
    if "call incoming" in lower or "incoming call" in lower:
        STATE.update("sip", state="call_ringing")
        STATE.event("sip", "incoming call ringing")
    call_match = re.search(r"Call established: ([^\n]+)", line)
    if call_match:
        label = call_match.group(1)
        outbound_request = take_pending_outbound_call(label)
        STATE.update(
            "sip",
            state="call_established",
            last_call=label,
            last_call_started_at=utc_now(),
            last_call_ended_at=None,
        )
        STATE.event("sip", f"call established: {label}")
        start_bridge(label, outbound_request)
    termination = re.search(r"terminated \(duration: ([^)]+)\)", line)
    if termination:
        STATE.update(
            "sip",
            state="call_ended",
            last_call_duration=termination.group(1),
            last_call_ended_at=utc_now(),
        )
        STATE.event("sip", f"call ended after {termination.group(1)}")
        complete_outbound_call(termination.group(1))
        stop_bridge()
    rtp = re.search(r"audio=([0-9]+/[0-9]+) \(bit/s\)", line)
    if rtp:
        STATE.update("sip", rtp_seen=True, last_audio_bitrate=rtp.group(1))
    if "incoming rtp" in lower or "audio tx pipeline" in lower:
        STATE.update("sip", rtp_seen=True)


def stream_baresip_output(process: subprocess.Popen) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        append_log(line)
        handle_baresip_line(line)


def start_baresip() -> subprocess.Popen:
    STATE.update("sip", state="baresip_starting")
    process = subprocess.Popen(
        ["baresip", "-4", "-f", str(CONFIG_DIR), "-v"],
        stdin=subprocess.PIPE,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )
    STATE.update("sip", state="baresip_running", baresip_running=True, baresip_pid=process.pid)
    threading.Thread(target=stream_baresip_output, args=(process,), daemon=True).start()
    return process


def supervise_baresip() -> None:
    global baresip_process
    delay = 1
    while not stopping.is_set():
        baresip_process = start_baresip()
        code = baresip_process.wait()
        STATE.update("sip", baresip_running=False, baresip_pid=None, state="baresip_exited")
        stop_bridge()
        if stopping.is_set():
            break
        STATE.event("error", f"baresip exited with {code}; restarting in {delay}s")
        time.sleep(delay)
        delay = min(delay * 2, 30)


def tts_preview(text: str) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) <= 140:
        return clean
    return clean[:137] + "..."


def normalize_call_target(raw_target: str) -> str:
    value = raw_target.strip()
    if not value:
        raise ValueError("Enter a number or SIP URI to call.")
    if len(value) > OUTBOUND_TARGET_MAX:
        raise ValueError("Call target is too long.")

    if value.lower().startswith("sip:"):
        target = value
    elif "@" in value:
        target = f"sip:{value}"
    else:
        compact = re.sub(r"[\s().-]+", "", value)
        target = f"sip:{compact}@{SIP_SERVER}"

    if len(target) > OUTBOUND_TARGET_MAX + 8:
        raise ValueError("Call target is too long.")
    if not re.fullmatch(r"sip:[A-Za-z0-9+*#_.!~'()%:-]+@[A-Za-z0-9_.:-]+", target):
        raise ValueError("Use a phone number, extension, or SIP URI like sip:123@example.com.")
    return target


def send_baresip_command(command: str) -> None:
    if "\n" in command or "\r" in command:
        raise ValueError("Invalid baresip command.")
    process = baresip_process
    if process is None or process.poll() is not None:
        raise RuntimeError("baresip is not running yet.")
    if process.stdin is None:
        raise RuntimeError("baresip command input is unavailable.")
    with baresip_command_lock:
        process.stdin.write(command + "\n")
        process.stdin.flush()


def request_outbound_tts_call(raw_target: str, raw_text: str, consent: bool) -> None:
    global pending_outbound_call
    if not consent:
        raise ValueError("Confirm consent before placing the call.")
    text = raw_text.strip()
    if not text:
        raise ValueError("Enter text to speak on the call.")
    if len(text) > OUTBOUND_TTS_TEXT_MAX:
        raise ValueError(f"TTS text is too long; keep it under {OUTBOUND_TTS_TEXT_MAX} characters.")
    if active_bridge is not None:
        raise RuntimeError("A call is already active; wait for it to end before dialing.")
    if genai is None or types is None:
        raise RuntimeError("google-genai is not installed; TTS speech cannot be generated.")
    if not (ENV.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")):
        raise RuntimeError("GEMINI_API_KEY is missing; TTS speech cannot be generated.")

    target = normalize_call_target(raw_target)
    requested_at = utc_now()
    request = {
        "target": target,
        "tts_text": text,
        "requested_at": requested_at,
        "created_monotonic": time.monotonic(),
    }
    with outbound_lock:
        pending_outbound_call = request
        STATE.update(
            "outbound",
            state="dialing",
            last_target=target,
            last_requested_at=requested_at,
            last_connected_at=None,
            last_completed_at=None,
            last_duration=None,
            last_error=None,
            last_tts_preview=tts_preview(text),
        )
    try:
        send_baresip_command(f"/dial {target}")
    except Exception as exc:
        with outbound_lock:
            pending_outbound_call = None
            STATE.update("outbound", state="error", last_error=redact(str(exc)))
        raise
    STATE.event("outbound", f"outbound TTS dial requested for {target}")


def take_pending_outbound_call(call_label: str) -> dict[str, Any] | None:
    global pending_outbound_call
    with outbound_lock:
        request = pending_outbound_call
        if request is None:
            return None
        if time.monotonic() - float(request.get("created_monotonic", 0.0)) > 180:
            pending_outbound_call = None
            STATE.update("outbound", state="error", last_error="Outbound call timed out before connecting.")
            STATE.event("error", "outbound TTS call timed out before connecting")
            return None
        pending_outbound_call = None
        STATE.update("outbound", state="active", last_connected_at=utc_now(), last_error=None)
    STATE.event("outbound", f"outbound TTS call connected: {call_label}")
    return request


def complete_outbound_call(duration: str) -> None:
    outbound = STATE.snapshot().get("outbound", {})
    if outbound.get("state") not in ("active", "dialing"):
        return
    next_state = "completed" if outbound.get("state") == "active" else "ended_before_connect"
    STATE.update(
        "outbound",
        state=next_state,
        last_completed_at=utc_now(),
        last_duration=duration,
    )
    STATE.event("outbound", f"outbound TTS call {next_state} after {duration}")


def file_info(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    stat = path.stat()
    return {
        "exists": True,
        "bytes": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
    }


recordings_lock = threading.RLock()
RECORDINGS: list[dict[str, Any]] = []


def wav_info(path: Path, expected_bytes: int = 0) -> dict[str, Any]:
    info: dict[str, Any] = {
        "path": str(path),
        "filename": path.name,
        "url": f"/recordings/{path.name}",
        "exists": path.exists(),
    }
    size = path.stat().st_size if path.exists() else expected_bytes
    info["bytes"] = size
    if path.exists():
        stat = path.stat()
        info["modified"] = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
        duration = 0.0
        try:
            with wave.open(str(path), "rb") as handle:
                frames = handle.getnframes()
                rate = handle.getframerate() or 1
                duration = frames / float(rate)
                frames_remaining = min(frames, int(rate * WAV_ANALYSIS_MAX_SECONDS))
                total = 0
                samples = 0
                peak = 0
                while frames_remaining > 0:
                    data = handle.readframes(min(4096, frames_remaining))
                    if not data:
                        break
                    frames_remaining -= len(data) // max(1, handle.getnchannels() * handle.getsampwidth())
                    for i in range(0, len(data) - 1, 2):
                        sample = int.from_bytes(data[i : i + 2], "little", signed=True)
                        total += sample * sample
                        samples += 1
                        peak = max(peak, abs(sample))
                info["rms"] = int((total / max(samples, 1)) ** 0.5)
                info["peak"] = peak
                info["silent"] = peak < 50
        except Exception:
            pass
        info["duration_seconds"] = round(duration, 2)
    return info


def recording_alignment_warning(record: dict[str, Any]) -> str:
    caller_duration = (record.get("caller") or {}).get("duration_seconds")
    agent_duration = (record.get("agent") or {}).get("duration_seconds")
    if not isinstance(caller_duration, (int, float)) or not isinstance(agent_duration, (int, float)):
        return ""
    diff = agent_duration - caller_duration
    if abs(diff) < 0.5:
        return ""
    return (
        f"<div class='recording-warning'>Agent duration differs from caller by {diff:+.1f} s. "
        f"Older recordings may contain only generated speech instead of a timeline-aligned track.</div>"
    )


def scan_existing_recordings() -> None:
    if not RECORDINGS_DIR.exists():
        return
    with recordings_lock:
        RECORDINGS.clear()
        groups: dict[str, dict[str, Any]] = {}
        for path in RECORDINGS_DIR.iterdir():
            if not path.is_file() or not path.suffix == ".wav":
                continue
            name = path.stem
            kind, _, call_id = name.partition("-")
            if kind not in ("caller", "agent", "merged"):
                continue
            entry = groups.setdefault(call_id, {"call_id": call_id, "_paths": {}})
            entry["_paths"][kind] = path
            entry.setdefault("started_at", datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat())
            entry["ended_at"] = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        for call_id, entry in groups.items():
            paths = entry.pop("_paths")
            record = {
                "call_id": call_id,
                "started_at": entry.get("started_at"),
                "ended_at": entry.get("ended_at"),
                "caller": wav_info(paths["caller"]) if "caller" in paths else {"exists": False, "filename": f"caller-{call_id}.wav", "url": f"/recordings/caller-{call_id}.wav"},
                "agent": wav_info(paths["agent"]) if "agent" in paths else {"exists": False, "filename": f"agent-{call_id}.wav", "url": f"/recordings/agent-{call_id}.wav"},
                "merged": wav_info(paths["merged"]) if "merged" in paths else {"exists": False, "filename": f"merged-{call_id}.wav", "url": f"/recordings/merged-{call_id}.wav"},
            }
            RECORDINGS.append(record)
        RECORDINGS.sort(key=lambda r: r.get("ended_at") or r.get("started_at") or "", reverse=True)
        if len(RECORDINGS) > RECORDINGS_RETENTION:
            stale = RECORDINGS[RECORDINGS_RETENTION:]
            del RECORDINGS[RECORDINGS_RETENTION:]
            for old in stale:
                for info in (old.get("caller"), old.get("agent"), old.get("merged")):
                    path_str = info.get("path") if isinstance(info, dict) else None
                    if path_str:
                        try:
                            Path(path_str).unlink(missing_ok=True)
                        except OSError:
                            pass


def status() -> dict[str, Any]:
    with log_lock:
        lines = list(log_lines)
    code_journal, journal_text = run(
        ["journalctl", "-u", SERVICE_NAME, "-n", "220", "--no-pager", "--output", "short-iso"], timeout=8
    )
    journal_lines = journal_text.splitlines() if code_journal == 0 else [journal_text]
    process = baresip_process
    code, hostname = run(["hostname"], timeout=2)
    code_uptime, uptime = run(["uptime", "-p"], timeout=2)
    snap = STATE.snapshot()
    if process:
        snap["sip"]["baresip_running"] = process.poll() is None
        snap["sip"]["baresip_pid"] = process.pid if process.poll() is None else None
    with recordings_lock:
        recordings_view = [json.loads(json.dumps(r)) for r in RECORDINGS]
    return {
        "generated_at": utc_now(),
        "host": hostname if code == 0 else socket.gethostname(),
        "host_uptime": uptime if code_uptime == 0 else None,
        "extension": EXTENSION,
        "name": APP_NAME,
        "sip_server": SIP_SERVER,
        "public_site": PUBLIC_SITE,
        "model": GEMINI_MODEL,
        "state": snap,
        "files": {
            "config": file_info(CONFIG_DIR / "config"),
            "accounts": file_info(CONFIG_DIR / "accounts"),
        },
        "logs": lines,
        "systemd_logs": journal_lines,
        "recordings": recordings_view,
        "recordings_dir": str(RECORDINGS_DIR),
        "recordings_retention": RECORDINGS_RETENTION,
    }


def badge_class(value: str) -> str:
    value = str(value).lower()
    if any(token in value for token in ["error", "failed", "missing", "exited", "not_configured"]):
        return "bad"
    if any(token in value for token in ["starting", "connecting", "ringing", "interrupted", "complete"]):
        return "warn"
    if any(token in value for token in ["running", "registered", "connected", "listening", "responding", "ready", "in_call"]):
        return "ok"
    return "neutral"


def render_cards(section: dict[str, Any], wanted: list[tuple[str, str]]) -> str:
    cards = []
    for key, label in wanted:
        value = section.get(key)
        cls = badge_class(str(value)) if key == "state" else "neutral"
        cards.append(
            f"<section class='card {cls}'><div class='label'>{html.escape(label)}</div>"
            f"<div class='value'>{html.escape(str(value))}</div></section>"
        )
    return "".join(cards)


def format_bytes(value: Any) -> str:
    try:
        size = int(value)
    except (TypeError, ValueError):
        return "n/a"
    if size < 1024:
        return f"{size} B"
    units = ["KB", "MB", "GB"]
    for unit in units:
        size /= 1024.0
        if size < 1024:
            return f"{size:.1f} {unit}"
    return f"{size:.1f} TB"


def render_recording_track(label: str, info: dict[str, Any]) -> str:
    if not info or not info.get("exists"):
        return (
            f"<div class='track missing'>"
            f"<div class='track-label'>{html.escape(label)}</div>"
            f"<div class='track-detail'>not captured</div>"
            f"</div>"
        )
    filename = info.get("filename", "")
    url = info.get("url", "#")
    duration = info.get("duration_seconds")
    size = format_bytes(info.get("bytes", 0))
    duration_str = f"{duration:.1f} s" if isinstance(duration, (int, float)) and duration else "n/a"
    rms = info.get("rms")
    audio_state = "silent" if info.get("silent") else f"rms {rms}" if isinstance(rms, int) else "rms n/a"
    return (
        f"<div class='track'>"
        f"<div class='track-label'>{html.escape(label)}</div>"
        f"<audio controls preload='none' src='{html.escape(url)}'></audio>"
        f"<div class='track-detail'>{html.escape(duration_str)} - {html.escape(size)} - {html.escape(audio_state)} - <a href='{html.escape(url)}' download>download</a></div>"
        f"<div class='track-name'>{html.escape(filename)}</div>"
        f"</div>"
    )


def render_recordings(recordings: list[dict[str, Any]], recordings_dir: str, retention: int) -> str:
    header = (
        f"<p class='muted'>Stored in <code>{html.escape(recordings_dir)}</code>. "
        f"Most recent {int(retention)} calls retained. Each call produces three WAV tracks "
        f"(caller microphone, Gemini assistant audio, merged mix).</p>"
    )
    if not recordings:
        return header + "<p class='muted'>No recordings yet. Place a call to extension " + html.escape(EXTENSION) + " to generate one.</p>"
    items = []
    for record in recordings:
        call_id = record.get("call_id", "?")
        started = record.get("started_at") or "?"
        ended = record.get("ended_at") or "?"
        caller = render_recording_track("Caller", record.get("caller") or {})
        agent = render_recording_track("Agent (Gemini)", record.get("agent") or {})
        merged = render_recording_track("Merged mix", record.get("merged") or {})
        merge_status = "ok" if (record.get("merged") or {}).get("exists") else "pending"
        warning = recording_alignment_warning(record)
        items.append(
            f"<section class='recording'>"
            f"<header><div><b>Call {html.escape(str(call_id))}</b></div>"
            f"<div class='recording-meta'>started {html.escape(started)}<br>ended {html.escape(ended)} - merge: {html.escape(merge_status)}</div></header>"
            f"{warning}"
            f"<div class='tracks'>{caller}{agent}{merged}</div>"
            f"</section>"
        )
    return header + "".join(items)


def render_page(data: dict[str, Any]) -> bytes:
    snap = data["state"]
    service = snap["service"]
    sip = snap["sip"]
    gemini_state = snap["gemini"]
    audio = snap["audio"]
    conv = snap["conversation"]
    outbound = snap.get("outbound", {})
    overall_ok = sip.get("baresip_running") and sip.get("registered") and gemini_state.get("state") not in ("error", "dependency_missing")
    logs = html.escape("\n".join(data["logs"][-180:]))
    events = "".join(
        f"<li><span>{html.escape(e['at'])}</span><b>{html.escape(e['kind'])}</b>{html.escape(e['message'])}</li>"
        for e in snap["events"][-80:]
    )
    systemd_logs = html.escape("\n".join(data["systemd_logs"][-160:]))
    recordings_html = render_recordings(data.get("recordings", []), data.get("recordings_dir", ""), data.get("recordings_retention", RECORDINGS_RETENTION))
    outbound_parts = [f"status: {outbound.get('state', 'idle')}"]
    if outbound.get("last_target"):
        outbound_parts.append(f"target: {outbound.get('last_target')}")
    if outbound.get("last_requested_at"):
        outbound_parts.append(f"requested: {outbound.get('last_requested_at')}")
    if outbound.get("last_duration"):
        outbound_parts.append(f"duration: {outbound.get('last_duration')}")
    if outbound.get("last_tts_preview"):
        outbound_parts.append(f"text: {outbound.get('last_tts_preview')}")
    if outbound.get("last_error"):
        outbound_parts.append(f"error: {outbound.get('last_error')}")
    outbound_status = html.escape(" - ".join(str(part) for part in outbound_parts))
    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="refresh" content="30"><title>{html.escape(APP_TITLE)}</title>
<style>
:root {{ color-scheme: dark; --bg:#090b12; --panel:#151924; --text:#f5f7fb; --muted:#9aa4b5; --ok:#43d17a; --warn:#ffd166; --bad:#ff5d73; --neutral:#7aa2ff; --line:#293142; }}
body {{ margin:0; font:15px/1.45 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:radial-gradient(circle at top left,#243257,var(--bg) 42%); color:var(--text); }}
main {{ max-width:1320px; margin:0 auto; padding:32px 18px 56px; }} h1 {{ font-size:clamp(2.4rem,7vw,5.8rem); line-height:.88; margin:0 0 12px; letter-spacing:-.07em; }}
.hero {{ display:flex; gap:18px; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; margin-bottom:18px; }} .badge {{ display:inline-flex; align-items:center; gap:9px; padding:11px 15px; border-radius:999px; background:var(--panel); border:1px solid var(--line); font-weight:800; }}
.badge:before,.card:before {{ content:""; width:10px; height:10px; border-radius:50%; background:var(--bad); box-shadow:0 0 18px var(--bad); }} .badge.ok:before,.card.ok:before {{ background:var(--ok); box-shadow:0 0 18px var(--ok); }} .card.warn:before {{ background:var(--warn); box-shadow:0 0 18px var(--warn); }} .card.neutral:before {{ background:var(--neutral); box-shadow:0 0 18px var(--neutral); }}
.section-title {{ margin:26px 0 10px; color:#dce5ff; }} .grid,.call-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px; }} .card,.call-card,.panel {{ background:rgba(21,25,36,.9); border:1px solid var(--line); border-radius:18px; box-shadow:0 18px 50px rgba(0,0,0,.22); }} .card {{ padding:15px; min-height:82px; position:relative; }} .card:before {{ position:absolute; right:14px; top:14px; }} .call-card {{ padding:20px; }} .call-card.primary {{ background:linear-gradient(135deg,rgba(122,162,255,.28),rgba(67,209,122,.16)); border-color:#4f78d7; }} .call-number {{ display:block; margin-top:8px; font-size:clamp(2.4rem,8vw,5.2rem); line-height:.9; font-weight:900; letter-spacing:-.06em; }} .call-detail {{ margin-top:8px; color:var(--muted); overflow-wrap:anywhere; }}
.call-form-panel {{ margin-top:18px; background:linear-gradient(135deg,rgba(122,162,255,.18),rgba(21,25,36,.94)); }} .call-form {{ display:grid; grid-template-columns:minmax(180px,280px) minmax(260px,1fr) auto; gap:12px; align-items:end; }} .call-form label {{ display:flex; flex-direction:column; gap:6px; color:#dce5ff; font-weight:700; }} .call-form input,.call-form textarea {{ width:100%; box-sizing:border-box; border:1px solid var(--line); border-radius:12px; background:#070910; color:var(--text); padding:11px 12px; font:inherit; }} .call-form textarea {{ min-height:46px; resize:vertical; }} .call-form button {{ border:0; border-radius:12px; padding:12px 16px; background:#7aa2ff; color:#071021; font-weight:900; cursor:pointer; }} .call-form .consent {{ grid-column:1 / -1; flex-direction:row; align-items:center; color:var(--muted); font-weight:500; }} .call-form .consent input {{ width:auto; }} .outbound-status {{ margin-top:10px; color:var(--muted); overflow-wrap:anywhere; }}
.label {{ color:var(--muted); font-size:.76rem; text-transform:uppercase; letter-spacing:.09em; }} .value {{ margin-top:8px; overflow-wrap:anywhere; font-size:1.05rem; }} .panel {{ margin-top:18px; padding:18px; }} pre {{ overflow:auto; white-space:pre-wrap; word-break:break-word; background:#070910; border:1px solid var(--line); border-radius:14px; padding:14px; max-height:520px; }} a {{ color:#a8c7ff; }} ul.events {{ list-style:none; padding:0; margin:0; }} .events li {{ display:grid; grid-template-columns:210px 90px 1fr; gap:10px; padding:8px 0; border-bottom:1px solid var(--line); }} .events span,.events b {{ color:var(--muted); }}
.recording {{ border:1px solid var(--line); border-radius:14px; padding:14px; margin-bottom:14px; background:rgba(7,9,16,.55); }}
.recording header {{ display:flex; justify-content:space-between; align-items:flex-start; gap:10px; margin-bottom:10px; flex-wrap:wrap; }}
.recording-meta {{ color:var(--muted); font-size:.82rem; text-align:right; }}
.recording-warning {{ margin:0 0 10px; padding:9px 11px; border:1px solid rgba(255,209,102,.45); border-radius:10px; color:#ffe3a3; background:rgba(255,209,102,.08); font-size:.82rem; }}
.tracks {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; }}
.track {{ background:rgba(21,25,36,.9); border:1px solid var(--line); border-radius:12px; padding:12px; display:flex; flex-direction:column; gap:6px; }}
.track.missing {{ opacity:.55; border-style:dashed; }}
.track-label {{ color:#dce5ff; font-weight:700; font-size:.95rem; }}
.track audio {{ width:100%; }}
.track-detail {{ color:var(--muted); font-size:.78rem; overflow-wrap:anywhere; }}
.track-name {{ color:#6f7d96; font-family:ui-monospace, SFMono-Regular, Menlo, monospace; font-size:.72rem; overflow-wrap:anywhere; }}
.muted {{ color:var(--muted); }}
@media (max-width:760px) {{ .call-form {{ grid-template-columns:1fr; }} .events li {{ grid-template-columns:1fr; }} }}
</style><script>
async function refresh() {{ try {{ const r=await fetch('/status.json', {{cache:'no-store'}}); const j=await r.json(); document.getElementById('json').textContent=JSON.stringify(j.state,null,2); }} catch(e) {{}} }} setInterval(refresh, 2000); window.addEventListener('load', refresh);
</script></head><body><main>
<div class="hero"><div><h1>{html.escape(APP_TITLE)}</h1><p>Realtime SIP to Gemini Flash Live conversation service for extension {html.escape(data['extension'])}. Model: <code>{html.escape(GEMINI_MODEL)}</code>.</p><p><a href="/status.json">/status.json</a></p></div><div class="badge {'ok' if overall_ok else 'bad'}">{'online' if overall_ok else 'attention needed'}</div></div>
<section class="panel call-form-panel" aria-label="Make outbound TTS call"><h2>Make TTS Call</h2><form class="call-form" method="post" action="/call"><label>Number or SIP URI<input name="number" type="tel" autocomplete="tel" placeholder="9762 or +49123456789" maxlength="{OUTBOUND_TARGET_MAX}" required></label><label>Text to speak<textarea name="text" placeholder="Text the assistant should speak when the call connects" maxlength="{OUTBOUND_TTS_TEXT_MAX}" required></textarea></label><button type="submit">Call and Speak</button><label class="consent"><input name="consent" type="checkbox" value="yes" required> I confirm this call is consented and expected.</label></form><div class="outbound-status">{outbound_status}</div></section>
<section class="call-grid" aria-label="Call details"><div class="call-card primary"><div class="label">Call This Demo</div><span class="call-number">{html.escape(data['extension'])}</span><div class="call-detail">SIP extension on {html.escape(data['sip_server'])}</div></div><div class="call-card"><div class="label">Registration</div><div class="value">{'registered and ready' if sip.get('registered') else 'not registered'}</div><div class="call-detail">Calls auto-answer and bridge to Gemini Live.</div></div><div class="call-card"><div class="label">Public Status</div><div class="value"><a href="{html.escape(data['public_site'])}">{html.escape(data['public_site'])}</a></div><div class="call-detail">Live dashboard and state JSON.</div></div></section>
<h2 class="section-title">Service</h2><div class="grid">{render_cards(service, [('state','Service State'),('pid','App PID'),('started_at','Started'),('last_error','Last Error')])}</div>
<h2 class="section-title">SIP</h2><div class="grid">{render_cards(sip, [('state','SIP State'),('registered','Registered'),('baresip_running','baresip Running'),('baresip_pid','baresip PID'),('last_call','Last Call'),('last_call_duration','Last Duration'),('rtp_seen','RTP Seen'),('last_audio_bitrate','Audio Bitrate')])}</div>
<h2 class="section-title">Gemini Live</h2><div class="grid">{render_cards(gemini_state, [('state','Gemini State'),('connected','Connected'),('model','Model'),('language_code','Language'),('last_event','Last Event'),('reconnects','Reconnects'),('generation_complete_count','Generations'),('vad_turns','Local VAD Turns'),('audio_chunks_sent','Audio Chunks Sent'),('audio_chunks_dropped','Audio Dropped'),('vad_mode','VAD Mode'),('first_audio_latency_ms','First Audio Latency'),('input_transcript','Input Transcript'),('output_transcript','Output Transcript'),('last_error','Last Error')])}</div>
<h2 class="section-title">Audio Bridge</h2><div class="grid">{render_cards(audio, [('state','Audio State'),('caller_audio_active','Caller Speaking'),('assistant_audio_active','Assistant Speaking'),('barge_in_count','Barge-ins'),('input_queue_depth','Input Queue'),('output_queue_depth','Output Queue'),('last_input_rms','Input RMS'),('last_error','Last Error')])}</div>
<h2 class="section-title">Conversation</h2><div class="grid">{render_cards(conv, [('state','Conversation State'),('turn','Current Turn'),('call_id','Call ID'),('started_at','Started'),('ended_at','Ended'),('interruptions','Interruptions'),('last_user_activity_at','Last User Activity'),('last_assistant_activity_at','Last Assistant Activity')])}</div>
<section class="panel"><h2>Event Timeline</h2><ul class="events">{events}</ul></section>
<section class="panel"><h2>Live State JSON</h2><pre id="json">loading...</pre></section>
<section class="panel"><h2>Call Recordings</h2>{recordings_html}</section>
<section class="panel"><h2>Integrated App Logs</h2><pre>{logs}</pre></section>
<section class="panel"><h2>systemd journal</h2><pre>{systemd_logs}</pre></section>
</main></body></html>"""
    return body.encode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/recordings" or parsed.path.startswith("/recordings/"):
            self.serve_recording(parsed.path)
            return
        if parsed.path not in ("/", "/status.json"):
            self.send_error(404)
            return
        data = status()
        if parsed.path == "/status.json":
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

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/call":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400)
            return
        if length <= 0:
            self.send_error(400)
            return
        if length > 20_000:
            self.send_error(413)
            return
        params = parse_qs(self.rfile.read(length).decode("utf-8", errors="replace"), keep_blank_values=True)
        number = params.get("number", [""])[0]
        text = params.get("text", [""])[0]
        consent = params.get("consent", [""])[0] == "yes"
        try:
            request_outbound_tts_call(number, text, consent)
        except Exception as exc:
            clean_error = redact(str(exc))
            STATE.update("outbound", state="error", last_error=clean_error)
            STATE.event("error", f"outbound TTS request rejected: {clean_error}")
        self.send_response(303)
        self.send_header("Location", "/")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def serve_recording(self, path: str) -> None:
        relative = path[len("/recordings/"):] if path != "/recordings" else ""
        if not relative or "/" in relative or ".." in relative:
            self.send_error(404)
            return
        filename = unquote(relative)
        target = (RECORDINGS_DIR / filename).resolve()
        try:
            target.relative_to(RECORDINGS_DIR.resolve())
        except ValueError:
            self.send_error(404)
            return
        if not target.exists() or not target.is_file():
            self.send_error(404)
            return
        try:
            body = target.read_bytes()
        except OSError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Disposition", f'inline; filename="{filename}"')
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        append_log(f"{self.address_string()} - {format % args}")


def handle_signal(signum: int, frame: Any) -> None:
    stopping.set()
    stop_bridge()
    process = baresip_process
    if process and process.poll() is None:
        process.terminate()


def ensure_runtime(env: dict[str, str]) -> None:
    if not has_command("baresip"):
        raise SystemExit("baresip is required")
    if not has_command("ffmpeg"):
        raise SystemExit("ffmpeg is required")
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    scan_existing_recordings()
    run(["modprobe", "snd-aloop"], timeout=5)
    if genai is None:
        STATE.update("gemini", state="dependency_missing", last_error="google-genai is not installed")
    elif env.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY"):
        STATE.update("gemini", state="configured")
    else:
        STATE.update("gemini", state="not_configured", last_error="GEMINI_API_KEY missing")


def main() -> int:
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    ensure_runtime(ENV)
    write_baresip_config(ENV)
    STATE.update("service", state="running")
    threading.Thread(target=supervise_baresip, daemon=True).start()
    STATE.event("service", f"Serving {APP_TITLE} on http://{HOST}:{PORT}")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.timeout = 1
    while not stopping.is_set():
        server.handle_request()
    server.server_close()
    STATE.update("service", state="stopped")
    return 0


def alsa_loopback_test(playback: str, capture: str, seconds: float = 1.0) -> int:
    if not has_command("ffmpeg"):
        print("ffmpeg missing")
        return 1
    capture_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "alsa",
        "-ac",
        "1",
        "-ar",
        "8000",
        "-i",
        capture,
        "-t",
        str(seconds),
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "-ac",
        "1",
        "-ar",
        "8000",
        "pipe:1",
    ]
    play_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=880:duration={seconds}",
        "-f",
        "alsa",
        "-ac",
        "1",
        "-ar",
        "8000",
        playback,
    ]
    capture_proc = subprocess.Popen(capture_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(0.2)
    play_proc = subprocess.Popen(play_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        out, err = capture_proc.communicate(timeout=seconds + 4)
        _, play_err = play_proc.communicate(timeout=seconds + 4)
    except subprocess.TimeoutExpired:
        for proc in (capture_proc, play_proc):
            if proc.poll() is None:
                proc.terminate()
        out, err = capture_proc.communicate(timeout=2)
        _, play_err = play_proc.communicate(timeout=2)
        print(
            json.dumps(
                {
                    "ok": False,
                    "playback": playback,
                    "capture": capture,
                    "bytes": len(out),
                    "rms": pcm16_rms(out),
                    "reason": "ALSA loopback test timed out",
                    "capture_error": err.decode(errors="replace")[-500:],
                    "play_error": play_err.decode(errors="replace")[-500:],
                },
                indent=2,
            ),
            flush=True,
        )
        return 1
    rms = pcm16_rms(out)
    if capture_proc.returncode != 0 or play_proc.returncode != 0 or rms < 50:
        print(
            json.dumps(
                {
                    "ok": False,
                    "playback": playback,
                    "capture": capture,
                    "bytes": len(out),
                    "rms": rms,
                    "capture_error": err.decode(errors="replace")[-500:],
                    "play_error": play_err.decode(errors="replace")[-500:],
                },
                indent=2,
            )
        )
        return 1
    print(json.dumps({"ok": True, "playback": playback, "capture": capture, "bytes": len(out), "rms": rms}, indent=2))
    return 0


async def gemini_self_test(env: dict[str, str]) -> int:
    api_key = env.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key or genai is None or types is None:
        print(json.dumps({"ok": False, "reason": "Gemini key or dependency missing"}, indent=2), flush=True)
        return 1
    client = genai.Client(api_key=api_key)
    config = types.LiveConnectConfig(
        response_modalities=[types.Modality.AUDIO],
        system_instruction="Say only: Gemini live test successful.",
        thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL),
    )
    got_audio = 0
    got_complete = False
    try:
        async with client.aio.live.connect(model=GEMINI_MODEL, config=config) as session:
            await session.send_realtime_input(text="Please speak the short test phrase now.")
            receive = getattr(session, "_receive", None) or session.receive
            deadline = time.monotonic() + GEMINI_GENERATION_TIMEOUT_SECONDS
            while time.monotonic() < deadline:
                msg = await asyncio.wait_for(receive(), timeout=max(0.1, deadline - time.monotonic()))
                sc = getattr(msg, "server_content", None)
                if sc and getattr(sc, "model_turn", None):
                    for part in sc.model_turn.parts or []:
                        inline = getattr(part, "inline_data", None)
                        if inline and inline.data:
                            got_audio += len(inline.data)
                if sc and getattr(sc, "generation_complete", False):
                    got_complete = True
                if got_audio > 1000 and got_complete:
                    break
    except Exception as exc:
        print(json.dumps({"ok": False, "reason": redact(str(exc))}, indent=2), flush=True)
        return 1
    ok = got_audio > 1000 and got_complete
    print(json.dumps({"ok": ok, "audio_bytes": got_audio, "generation_complete": got_complete}, indent=2), flush=True)
    return 0 if ok else 1


def self_test() -> int:
    ensure_runtime(ENV)
    print("Gemini Live self-test", flush=True)
    gemini_code = asyncio.run(gemini_self_test(ENV))
    print("Inbound SIP audio loopback self-test", flush=True)
    inbound_code = alsa_loopback_test(BARESIP_AUDIO_PLAYER, SIP_INPUT_CAPTURE)
    print("Outbound assistant audio loopback self-test", flush=True)
    outbound_code = alsa_loopback_test(SIP_OUTPUT_PLAYBACK, BARESIP_AUDIO_SOURCE)
    data = status()
    render_page(data)
    print(json.dumps({"status_render_ok": True}, indent=2), flush=True)
    return 0 if gemini_code == 0 and inbound_code == 0 and outbound_code == 0 else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(self_test())
    raise SystemExit(main())
