#!/usr/bin/env python3
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "baresip-runtime"
WAV_PATH = ROOT / "rickroll.wav"


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


def write_config(env: dict[str, str]) -> None:
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


def main() -> int:
    env = load_env(ROOT / ".env")
    mp3_path = Path(require(env, "RICKROLL_MP3")).expanduser().resolve()
    if not mp3_path.exists():
        raise SystemExit(f"MP3 file does not exist: {mp3_path}")
    convert_mp3(mp3_path)
    write_config(env)
    return subprocess.call(["baresip", "-4", "-f", str(CONFIG_DIR), "-v"])


if __name__ == "__main__":
    raise SystemExit(main())
