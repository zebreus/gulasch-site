#!/usr/bin/env python3
from pathlib import Path

WEB_ROOT = Path("/var/www/bagger.gulasch.site")


def assert_contains(text, needle, label):
    if needle not in text:
        raise AssertionError(f"missing {label}: {needle}")


def main():
    html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    script = (WEB_ROOT / "script.js").read_text(encoding="utf-8")

    for needle, label in [
        ('data-action="date"', "rendezvous quick-menu button"),
        ('id="date-invite"', "future-date invite button"),
        ('id="date-start"', "immediate-date button"),
        ('id="screen-schedule"', "schedule overlay"),
        ('id="screen-status"', "status overlay"),
        ('id="screen-save"', "save overlay"),
    ]:
        assert_contains(html, needle, label)

    for needle, label in [
        ("case 'date': openDate();", "date quick-menu handler"),
        ("action: 'invite_date'", "future-date API call"),
        ("action: 'start_date'", "immediate-date API call"),
        ("function renderShopCards", "shop rendering"),
        ("function isShopOpen", "shop day gating"),
        ("gameData.choiceSets[scene.category]", "category choices"),
        ("settings.showFreeText === false", "freetext visibility toggle"),
    ]:
        assert_contains(script, needle, label)

    print("ok ui_smoke_test")


if __name__ == "__main__":
    main()
