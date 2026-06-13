# Richard SIP Bot

Integrated Python app for extension `9415` (`richard-sip`).

One process does both jobs:

- supervises `baresip` for SIP registration, auto-answer, and audio playback
- serves the public live status/log page on `127.0.0.1:8095`

Public URL:

```text
https://richard.gulasch.site
```

Systemd service:

```sh
systemctl status rickroll-sip.service
systemctl restart rickroll-sip.service
journalctl -u rickroll-sip.service -f
```

The status page redacts credential-like values and does not expose the SIP password.
