# Conversation Demo SIP Bot

Integrated Python app for extension `9762` (`conversation-demo`).

It supervises `baresip` for SIP auto-answer, bridges active calls to Gemini 3.1 Flash Live, and serves a public live status/log page on `127.0.0.1:8096`.

Public URL:

```text
https://conversation.gulasch.site
```

Systemd service:

```sh
systemctl status conversation-sip.service
systemctl restart conversation-sip.service
journalctl -u conversation-sip.service -f
```

The status page redacts credential-like values and does not expose the SIP password.

## Runtime behavior

- SIP audio uses `baresip` with ALSA loopback devices instead of static WAV playback.
- Caller audio is captured from ALSA, resampled to 16 kHz PCM, and streamed to `gemini-3.1-flash-live-preview`.
- Gemini audio is received as 24 kHz PCM, resampled to 8 kHz, and played back into the SIP call.
- Gemini speech output is configured for German (`de-DE`) and the system prompt requires German responses.
- Local VAD detects caller utterances and sends each completed utterance to a fresh Gemini Live session. This avoids the Developer API's single-response behavior after `audio_stream_end` while still streaming each utterance in real time.
- Local barge-in detection clears queued assistant audio when caller speech is detected while Gemini is speaking.
- Agent recordings are timeline-preserving: silence is written before and between Gemini turns so the agent track aligns with the caller and merged tracks.
- `/status.json` and the dashboard expose separate service, SIP, Gemini, audio bridge, and conversation states.

## Self-test

Run the built-in integration checks from this directory:

```sh
python3 conversation_app.py --self-test
```

The self-test verifies Gemini Live audio response generation, both ALSA loopback directions, and dashboard rendering.
