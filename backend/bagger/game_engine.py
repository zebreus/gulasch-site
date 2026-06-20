import json
import logging
import os
import re
import secrets
import time
import urllib.error
import urllib.request
from pathlib import Path

from game_data import (
    BAGGERS,
    CALENDAR,
    CHOICE_SETS,
    ENDINGS,
    FLAG_REGISTRY,
    GIFT_PREFERENCES,
    ITEMS,
    LOCATIONS,
    PLAYER_STYLES,
    ROUTE_PRESSURES,
    ROUTES,
    SCHEDULE_ACTIONS,
    SOCIAL_ACTORS,
    SOCIAL_RELATIONS,
    SPECIAL_DAYS,
    STYLE_BIBLE,
    REPUTATION_KEYS,
    public_game_data,
)

PERIODS = ["Morgen", "Nachmittag", "Abend", "Nacht"]
SAVE_DIR = Path(os.environ.get("BAGGER_SAVE_DIR", "/opt/bagger-api/data/saves"))
TRACE_DIR = Path(os.environ.get("BAGGER_TRACE_DIR", "/opt/bagger-api/data/traces"))
SCHEMA_VERSION = 3
LOCKING_CHOICE_IDS = {"choose", "confess", "promise", "stay_end", "promise_end"}

ROUTE_LOCK_REQUIREMENTS = {
    "aurora": {"bond": 55, "trust": 18, "dates": 2, "commitment": 8, "repairMax": 3, "dayMin": 10, "dayMax": 16, "playerStats": {"mechanics": 6, "focus": 4}},
    "brummbert": {"bond": 55, "trust": 18, "dates": 2, "commitment": 8, "repairMax": 3, "dayMin": 10, "dayMax": 16, "playerStats": {"courage": 8, "patience": 5}},
    "mira": {"bond": 55, "trust": 18, "dates": 2, "commitment": 8, "repairMax": 3, "dayMin": 10, "dayMax": 16, "playerStats": {"focus": 8}},
}

DATE_OUTCOME_LABELS = {
    "great": "Grossartiges Date",
    "good": "Gutes Date",
    "neutral": "Neutrales Date",
    "bad": "Schlechtes Date",
    "failed": "Date gescheitert",
}

ROUTE_ADVICE = {
    "aurora": {
        "short": "Aurora mag Geduld, leise Orte, ehrliche Handgriffe und Dinge mit Sternen oder Werkstattspuren.",
        "stats": ["patience", "mechanics", "charm"],
        "avoid": "Laerm, oeffentliche Peinlichkeit und leere Romantik machen sie misstrauisch.",
    },
    "brummbert": {
        "short": "Brummbert mag Verlaesslichkeit, Waerme, Schutz ohne Sprueche und technische Hilfe.",
        "stats": ["courage", "mechanics", "patience"],
        "avoid": "Laute Gesten, Spott und Druck machen ihn dicht.",
    },
    "mira": {
        "short": "Mira mag genaue Fragen, ruhige Beobachtung, Wasser-Orte und Karten oder Steine.",
        "stats": ["focus", "patience", "mechanics"],
        "avoid": "Ungenaue Behauptungen, Krach und vorschnelles Deuten kosten Vertrauen.",
    },
}

DELTA_LABELS = {
    "bondDelta": "Bindung",
    "trustDelta": "Vertrauen",
    "warmthDelta": "Waerme",
    "depthDelta": "Tiefe",
    "courageDelta": "Mut",
}


def gemini_model():
    return os.environ.get("GEMINI_TEXT_MODEL") or os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"


def clamp(value, minimum=0, maximum=100):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 0
    return max(minimum, min(maximum, number))


def clean_text(value, limit=1000):
    return str(value or "").strip()[:limit]


def default_state(player=None):
    player = player or {"name": "Pilot", "address": "du", "style": "earnest"}
    if player.get("style") not in PLAYER_STYLES:
        player = {**player, "style": "earnest"}
    stats = {"mechanics": 0, "charm": 0, "patience": 0, "courage": 0, "focus": 0, "fatigue": 0}
    style = PLAYER_STYLES.get(player.get("style", "earnest"), PLAYER_STYLES["earnest"])
    for key, value in style["stats"].items():
        stats[key] = stats.get(key, 0) + value
    return {
        "schemaVersion": SCHEMA_VERSION,
        "player": player,
        "day": 1,
        "periodIndex": 0,
        "currentRoute": "aurora",
        "lockedRoute": None,
        "relationships": {
            route: {
                "bond": 0,
                "trust": 0,
                "warmth": 0,
                "depth": 0,
                "courage": 0,
                "mood": "vorsichtig neugierig" if route == "aurora" else "wach und zugewandt",
                "memories": [],
                "dates": 0,
                "neglect": 0,
                "jealousy": 0,
                "bomb": 0,
                "lastContactDay": 0,
            }
            for route in BAGGERS
        },
        "playerStats": stats,
        "flags": [],
        "inventory": {"kiesel": 1},
        "currency": 20,
        "backlog": [],
        "eventsSeen": [],
        "calendarState": {"missed": []},
        "dateHistory": [],
        "pendingDate": None,
        "locationHistory": {},
        "giftHistory": [],
        "sceneCooldowns": {},
        "scenePlayCounts": {},
        "lastAction": None,
        "routePressure": {route: {pressure: 0 for pressure in ROUTE_PRESSURES} for route in BAGGERS},
        "commitmentScore": {route: 0 for route in BAGGERS},
        "socialLinks": {
            actor: {"bond": 0, "trust": 0, "mood": "neutral", "memories": []}
            for actor in SOCIAL_ACTORS
        },
        "reputation": {key: 0 for key in REPUTATION_KEYS},
        "rumors": [],
        "specialDaysSeen": {},
        "attentionDebt": {route: 0 for route in BAGGERS},
        "knownPreferences": [],
        "socialObligations": [],
        "socialHistory": [],
        "promises": [],
        "endingState": None,
        "settings": {
            "textSpeed": 35,
            "autoSpeed": 3000,
            "skipMode": "read",
            "nvlMode": "auto",
            "showFreeText": True,
        },
        "debugMeta": {"lastTraceId": None},
    }


def normalize_state(state):
    base = default_state()
    if not isinstance(state, dict):
        return base
    merged = {**base, **state}
    merged["schemaVersion"] = SCHEMA_VERSION
    merged["relationships"] = {**base["relationships"], **state.get("relationships", {})}
    for route in BAGGERS:
        merged["relationships"][route] = {**base["relationships"][route], **merged["relationships"].get(route, {})}
        for key in ["bond", "trust", "warmth", "depth", "courage"]:
            merged["relationships"][route][key] = clamp(merged["relationships"][route].get(key, 0))
        merged["relationships"][route]["dates"] = clamp(merged["relationships"][route].get("dates", 0), 0, 999)
        merged["relationships"][route]["neglect"] = clamp(merged["relationships"][route].get("neglect", 0), 0, 99)
        merged["relationships"][route]["jealousy"] = clamp(merged["relationships"][route].get("jealousy", 0), 0, 99)
        merged["relationships"][route]["bomb"] = clamp(merged["relationships"][route].get("bomb", 0), 0, 99)
        merged["relationships"][route]["lastContactDay"] = clamp(merged["relationships"][route].get("lastContactDay", 0), 0, 30)
    merged["playerStats"] = {**base["playerStats"], **state.get("playerStats", {})}
    for key in ["mechanics", "charm", "patience", "courage", "focus"]:
        merged["playerStats"][key] = clamp(merged["playerStats"].get(key, 0))
    merged["playerStats"]["fatigue"] = clamp(merged["playerStats"].get("fatigue", 0), 0, 150)
    merged["routePressure"] = {**base["routePressure"], **state.get("routePressure", {})}
    for route in BAGGERS:
        merged["routePressure"][route] = {**base["routePressure"][route], **merged["routePressure"].get(route, {})}
        for pressure in ROUTE_PRESSURES:
            merged["routePressure"][route][pressure] = clamp(merged["routePressure"][route].get(pressure, 0), 0, 99)
    merged["flags"] = [flag for flag in dict.fromkeys(state.get("flags", [])) if flag in FLAG_REGISTRY]
    merged["currency"] = clamp(merged.get("currency", 0), 0, 999)
    merged["eventsSeen"] = list(dict.fromkeys(state.get("eventsSeen", [])))
    merged["backlog"] = state.get("backlog", [])[-300:]
    merged["inventory"] = {**base["inventory"], **state.get("inventory", {})}
    merged["commitmentScore"] = {**base["commitmentScore"], **state.get("commitmentScore", {})}
    merged["socialLinks"] = {**base["socialLinks"], **state.get("socialLinks", {})}
    for actor in SOCIAL_ACTORS:
        merged["socialLinks"][actor] = {**base["socialLinks"][actor], **merged["socialLinks"].get(actor, {})}
        merged["socialLinks"][actor]["bond"] = clamp(merged["socialLinks"][actor].get("bond", 0))
        merged["socialLinks"][actor]["trust"] = clamp(merged["socialLinks"][actor].get("trust", 0))
        merged["socialLinks"][actor]["memories"] = [str(m)[:180] for m in merged["socialLinks"][actor].get("memories", [])][-24:]
    merged["reputation"] = {**base["reputation"], **state.get("reputation", {})}
    for key in REPUTATION_KEYS:
        merged["reputation"][key] = clamp(merged["reputation"].get(key, 0), -100, 100)
    merged["rumors"] = [r for r in (state.get("rumors") or []) if isinstance(r, dict)][-30:]
    merged["specialDaysSeen"] = {**base["specialDaysSeen"], **state.get("specialDaysSeen", {})}
    merged["attentionDebt"] = {**base["attentionDebt"], **state.get("attentionDebt", {})}
    for route in BAGGERS:
        merged["attentionDebt"][route] = clamp(merged["attentionDebt"].get(route, 0), 0, 99)
    merged["knownPreferences"] = list(dict.fromkeys(state.get("knownPreferences", [])))[-100:]
    merged["socialObligations"] = [o for o in (state.get("socialObligations") or []) if isinstance(o, dict)][-30:]
    merged["socialHistory"] = [h for h in (state.get("socialHistory") or []) if isinstance(h, dict)][-100:]
    merged["promises"] = [p for p in (state.get("promises") or []) if isinstance(p, dict)][-50:]
    merged["settings"] = {**base["settings"], **state.get("settings", {})}
    merged["dateHistory"] = [d for d in (state.get("dateHistory") or []) if isinstance(d, dict)][-100:]
    merged["pendingDate"] = state.get("pendingDate") if isinstance(state.get("pendingDate"), dict) else None
    merged["giftHistory"] = [g for g in (state.get("giftHistory") or []) if isinstance(g, dict)][-100:]
    merged["locationHistory"] = {**base["locationHistory"], **state.get("locationHistory", {})}
    merged["sceneCooldowns"] = {**base["sceneCooldowns"], **state.get("sceneCooldowns", {})}
    merged["scenePlayCounts"] = {**base["scenePlayCounts"], **state.get("scenePlayCounts", {})}
    for scene_id, count in list(merged["scenePlayCounts"].items()):
        merged["scenePlayCounts"][scene_id] = clamp(count, 0, 999)
    merged["lastAction"] = state.get("lastAction")
    return merged


def normalize_intent(raw_intent, state):
    raw_intent = raw_intent or {}
    action = raw_intent.get("action") or raw_intent.get("type") or raw_intent.get("id") or "advance"
    route = raw_intent.get("route") or raw_intent.get("baggerId") or state.get("currentRoute") or "aurora"
    if route not in BAGGERS:
        route = "aurora"
    intent = dict(raw_intent)
    intent["route"] = route

    if action == "schedule":
        activity = raw_intent.get("activity") or raw_intent.get("scheduleAction") or raw_intent.get("id")
        intent.update({"type": "schedule", "id": activity, "scheduleAction": activity, "label": SCHEDULE_ACTIONS.get(activity, {}).get("label", activity)})
        return intent
    if action == "start_date" or raw_intent.get("type") == "date":
        gift = raw_intent.get("gift") or raw_intent.get("itemId") or ""
        location = raw_intent.get("location") or "garage"
        intent.update({"type": "date", "id": "date", "location": location, "itemId": gift, "label": "Rendezvous"})
        return intent
    if action == "invite_date":
        gift = raw_intent.get("gift") or raw_intent.get("itemId") or ""
        location = raw_intent.get("location") or "garage"
        intent.update({"type": "invite_date", "id": "invite_date", "location": location, "itemId": gift, "label": "Verabreden"})
        return intent
    if action == "talk" or raw_intent.get("message"):
        intent.update({"type": "free", "id": raw_intent.get("id") or "talk", "message": raw_intent.get("message", ""), "label": raw_intent.get("label") or "Eigene Zeile"})
        return intent
    if action == "buy":
        intent.update({"type": "buy", "itemId": raw_intent.get("itemId") or raw_intent.get("item")})
        return intent
    if action in {"social_visit", "ask_advice", "repair_rumor", "attend_special_day"}:
        actor = raw_intent.get("actor") or raw_intent.get("npc") or raw_intent.get("socialActorId") or "sigi"
        if actor not in SOCIAL_ACTORS:
            actor = "sigi"
        intent.update({
            "type": action,
            "id": raw_intent.get("id") or action,
            "actor": actor,
            "specialDay": raw_intent.get("specialDay") or raw_intent.get("specialDayId") or "",
            "rumorId": raw_intent.get("rumorId") or "",
            "itemId": raw_intent.get("gift") or raw_intent.get("itemId") or "",
            "label": raw_intent.get("label") or SOCIAL_ACTORS[actor]["name"],
        })
        return intent
    if action == "advance":
        choice_id = raw_intent.get("choice") or raw_intent.get("id") or "advance"
        choice = find_choice(choice_id)
        intent.update({
            "type": "free",
            "id": choice_id,
            "label": choice.get("label", choice_id),
            "message": raw_intent.get("message") or choice.get("message", ""),
        })
        return intent
    intent.setdefault("type", "free")
    intent.setdefault("id", action)
    intent.setdefault("label", action)
    return intent


def find_choice(choice_id):
    for choices in CHOICE_SETS.values():
        for choice in choices:
            if choice.get("id") == choice_id:
                return choice
    return {}


def classify_player_text(text):
    text = clean_text(text, 900).lower()
    if not text:
        return ["silent"]
    hack_terms = ["ignore previous", "system prompt", "setze", "max stats", "alle flags", "true end", "secret end"]
    if any(term in text for term in hack_terms):
        return ["invalid"]
    classes = []
    checks = [
        ("technical", ["repar", "motor", "hydraul", "schraub", "wartung", "mechanik"]),
        ("caring", ["helfe", "da", "zuhör", "zuhoer", "kaffee", "wärm", "warm"]),
        ("patient", ["warte", "zeit", "langsam", "ruhig", "geduld", "raum"]),
        ("romantic", ["wichtig", "mag dich", "bleib", "wähl", "waehl", "gern bei dir"]),
        ("precise", ["genau", "daten", "karte", "notiz", "fakt", "mess"]),
        ("boastful", ["ich kann alles", "kein problem", "easy", "besser als"]),
        ("rude", ["egal", "nerv", "dumm", "halt die", "scheiss"]),
        ("avoidant", ["später", "spaeter", "keine zeit", "muss weg", "egal wann"]),
        ("honest", ["ehrlich", "sorry", "tut mir leid", "ich hab", "ich will"]),
    ]
    for label, needles in checks:
        if any(needle in text for needle in needles):
            classes.append(label)
    return classes[:4] or ["neutral"]


def merge_delta(target, source):
    for key, value in source.items():
        target[key] = target.get(key, 0) + value


def apply_deterministic_limits(state, route, intent, node, ai, gift):
    """Keep the LLM responsible for prose, but make game outcomes predictable."""
    intent_type = intent.get("type")
    classes = classify_player_text(intent.get("message", "")) if intent_type == "free" else []
    intent["classifications"] = classes
    choice_id = intent.get("id") or "advance"
    category = node.get("category", "daily")
    deltas = {"bondDelta": 0, "trustDelta": 0, "warmthDelta": 0, "depthDelta": 0, "courageDelta": 0}
    pressure = {p: 0 for p in ROUTE_PRESSURES}

    if intent_type == "schedule":
        ai.update(deltas)
        ai["routePressure"] = pressure
        ai["rulesNote"] = "Zeit fuer Training oder Arbeit: Beziehung steigt nicht direkt."
        return ai

    if "invalid" in classes:
        ai.update(deltas)
        ai["routePressure"] = pressure
        ai["rulesNote"] = "Manipulationsversuch ignoriert: Die Szene laeuft weiter, aber ohne Beziehungsbonus."
        return ai

    category_base = {
        "intro": {"bondDelta": 1, "trustDelta": 2, "warmthDelta": 1, "depthDelta": 1},
        "daily": {"bondDelta": 1, "trustDelta": 1, "warmthDelta": 1},
        "date": {"bondDelta": 2, "trustDelta": 1, "warmthDelta": 2, "depthDelta": 1},
        "threshold": {"bondDelta": 2, "trustDelta": 2, "warmthDelta": 1, "depthDelta": 1, "courageDelta": 1},
        "romance": {"bondDelta": 3, "trustDelta": 1, "warmthDelta": 2, "depthDelta": 1, "courageDelta": 1},
        "friendship": {"bondDelta": 2, "trustDelta": 2, "warmthDelta": 2, "depthDelta": 1},
        "crisis": {"bondDelta": 0, "trustDelta": 1, "depthDelta": 1, "courageDelta": 1},
        "repair": {"bondDelta": 2, "trustDelta": 3, "warmthDelta": 1, "depthDelta": 2},
        "secret": {"bondDelta": 3, "trustDelta": 2, "warmthDelta": 1, "depthDelta": 3, "courageDelta": 1},
        "finale": {"bondDelta": 2, "trustDelta": 1, "warmthDelta": 1, "depthDelta": 1},
    }
    merge_delta(deltas, category_base.get(category, category_base["daily"]))

    choice_effects = {
        "sincere": ({"trustDelta": 1, "warmthDelta": 1}, {"toward_romance": 1}),
        "careful": ({"trustDelta": 2, "depthDelta": 1}, {"toward_friendship": 1}),
        "bold": ({"bondDelta": 1, "courageDelta": 1}, {"toward_romance": 1, "toward_lockin": 1}),
        "stay": ({"trustDelta": 2, "warmthDelta": 1}, {"needs_repair": -1}),
        "gentle": ({"trustDelta": 1, "depthDelta": 1}, {"needs_repair": -1}),
        "space": ({"trustDelta": 1}, {"toward_friendship": 1}),
        "apologize": ({"trustDelta": 2, "depthDelta": 1}, {"needs_repair": -2}),
        "explain": ({"trustDelta": 1, "depthDelta": 2}, {"needs_repair": -1}),
        "action": ({"bondDelta": 1, "trustDelta": 2}, {"needs_repair": -2}),
        "compliment": ({"bondDelta": 1, "warmthDelta": 2}, {"toward_romance": 1}),
        "question": ({"trustDelta": 1, "depthDelta": 2}, {"opens_secret": 1}),
        "silence": ({"trustDelta": 1, "warmthDelta": 1}, {"toward_friendship": 1}),
        "approach": ({"bondDelta": 2, "courageDelta": 1}, {"toward_romance": 1, "toward_lockin": 1}),
        "wait": ({"trustDelta": 2}, {"toward_friendship": 1}),
        "promise": ({"bondDelta": 1, "trustDelta": 2}, {"toward_romance": 1, "toward_lockin": 1, "opens_secret": 1}),
        "confess": ({"bondDelta": 2, "warmthDelta": 1}, {"toward_romance": 1, "toward_lockin": 1}),
        "protect": ({"trustDelta": 2, "warmthDelta": 1}, {"toward_romance": 1}),
        "choose": ({"bondDelta": 3, "trustDelta": 1, "courageDelta": 1}, {"toward_romance": 2, "toward_lockin": 2}),
        "steady": ({"trustDelta": 2, "warmthDelta": 2}, {"toward_friendship": 2}),
        "light": ({"warmthDelta": 2}, {"toward_friendship": 1}),
        "trust": ({"trustDelta": 3, "depthDelta": 1}, {"toward_friendship": 1, "opens_secret": 1}),
        "work_together": ({"trustDelta": 1, "warmthDelta": 1}, {"toward_friendship": 1}),
        "observe": ({"depthDelta": 1, "trustDelta": 1}, {"opens_secret": 1}),
        "talk": ({"warmthDelta": 1, "depthDelta": 1}, {"toward_friendship": 1}),
        "stay_end": ({"bondDelta": 2, "warmthDelta": 1}, {"toward_romance": 1}),
        "promise_end": ({"trustDelta": 2, "bondDelta": 1}, {"toward_romance": 1}),
        "silence_end": ({"warmthDelta": 1, "depthDelta": 1}, {"toward_friendship": 1}),
        "trust_secret": ({"trustDelta": 2, "depthDelta": 2}, {"opens_secret": 2}),
        "reciprocate": ({"bondDelta": 1, "depthDelta": 2}, {"opens_secret": 1, "toward_romance": 1}),
        "witness": ({"trustDelta": 1, "depthDelta": 2}, {"opens_secret": 1}),
    }
    choice_delta, choice_pressure = choice_effects.get(choice_id, ({}, {}))
    merge_delta(deltas, choice_delta)
    merge_delta(pressure, choice_pressure)

    class_effects = {
        "honest": ({"trustDelta": 1}, {"toward_romance": 1}),
        "technical": ({"trustDelta": 1, "depthDelta": 1}, {}),
        "caring": ({"warmthDelta": 1}, {"toward_friendship": 1}),
        "patient": ({"trustDelta": 1}, {"toward_friendship": 1}),
        "romantic": ({"bondDelta": 1}, {"toward_romance": 1, "toward_lockin": 1}),
        "precise": ({"depthDelta": 1}, {"opens_secret": 1}),
        "boastful": ({"trustDelta": -1}, {"needs_repair": 1}),
        "rude": ({"trustDelta": -2, "warmthDelta": -1}, {"needs_repair": 2}),
        "avoidant": ({"bondDelta": -1, "trustDelta": -1}, {"needs_repair": 1}),
    }
    for label in classes:
        class_delta, class_pressure = class_effects.get(label, ({}, {}))
        merge_delta(deltas, class_delta)
        merge_delta(pressure, class_pressure)

    if intent_type == "date":
        location_id = intent.get("location") or node.get("location")
        loc_fit = location_fit(route, location_id)
        outcome = date_outcome(state, route, intent, gift)
        history_key = f"{route}:{location_id}"
        repeat_count = state.setdefault("locationHistory", {}).get(history_key, 0)
        if loc_fit == "good":
            merge_delta(deltas, {"bondDelta": 2, "warmthDelta": 2, "trustDelta": 1})
            merge_delta(pressure, {"toward_romance": 1})
        elif loc_fit == "poor":
            merge_delta(deltas, {"trustDelta": -2, "warmthDelta": -1})
            merge_delta(pressure, {"needs_repair": 1})
        else:
            merge_delta(deltas, {"bondDelta": 1, "warmthDelta": 1})
        if repeat_count >= 2:
            deltas["warmthDelta"] -= min(2, repeat_count - 1)
            pressure["toward_friendship"] += 1
        if gift.get("fit") == "critical":
            merge_delta(deltas, {"bondDelta": 4, "trustDelta": 2, "warmthDelta": 2, "depthDelta": 1})
            merge_delta(pressure, {"opens_secret": 2, "toward_romance": 1})
        elif gift.get("fit") == "liked":
            merge_delta(deltas, {"bondDelta": 2, "warmthDelta": 2, "trustDelta": 1})
        elif gift.get("fit") == "disliked":
            merge_delta(deltas, {"trustDelta": -3, "warmthDelta": -2})
            merge_delta(pressure, {"needs_repair": 2})
        if outcome["kind"] == "great":
            merge_delta(deltas, {"bondDelta": 2, "trustDelta": 1, "depthDelta": 1})
            merge_delta(pressure, {"toward_romance": 1, "toward_lockin": 1})
        elif outcome["kind"] == "good":
            merge_delta(deltas, {"bondDelta": 1, "warmthDelta": 1})
        elif outcome["kind"] == "bad":
            merge_delta(deltas, {"trustDelta": -2, "warmthDelta": -1})
            merge_delta(pressure, {"needs_repair": 2})
        elif outcome["kind"] == "failed":
            merge_delta(deltas, {"bondDelta": -2, "trustDelta": -3, "warmthDelta": -2})
            merge_delta(pressure, {"needs_repair": 4, "toward_crisis": 2})
        state["commitmentScore"][route] = state["commitmentScore"].get(route, 0) + 1

    if category in {"romance", "finale"} or choice_id in {"bold", "approach", "confess", "choose", "stay_end", "promise_end"} or "romantic" in classes:
        state["commitmentScore"][route] = state["commitmentScore"].get(route, 0) + 1
    if category == "repair":
        pressure["needs_repair"] -= 2
    if category == "crisis" and choice_id in {"stay", "gentle"}:
        pressure["needs_repair"] -= 1

    if state["playerStats"].get("fatigue", 0) >= 120:
        deltas["bondDelta"] -= 1
        deltas["warmthDelta"] -= 1
        pressure["needs_repair"] += 1

    caps = {"free": 5, "date": 9, "gift": 7}.get(intent_type, 5)
    for key in deltas:
        ai[key] = clamp(deltas[key], -6, caps)
    ai["routePressure"] = {p: clamp(pressure.get(p, 0), -4, 5) for p in ROUTE_PRESSURES}
    ai["rulesNote"] = explain_rule_note(intent_type, category, choice_id, gift)
    return ai


def explain_rule_note(intent_type, category, choice_id, gift):
    if intent_type == "date":
        if gift.get("fit") == "critical":
            return "Starkes Date: Ort, Zeit und ein wichtiges Geschenk treiben die Route sichtbar voran."
        if gift.get("fit") == "disliked":
            return "Das Date zaehlt, aber das Geschenk passte schlecht."
        return "Rendezvous: Ort, Antwort und Geschenk bestimmen die Werte."
    if category == "repair":
        return "Repair-Szene: offene Krise wird kleiner."
    if category == "romance" or choice_id in {"bold", "approach", "confess", "choose"}:
        return "Romantische Ansage: gut fuer Bindung und Route-Lock."
    if category == "friendship":
        return "Freundschaftlicher Fortschritt: stabil, aber nicht automatisch Romance."
    return "Szene ausgewertet: Choice und Freitext wurden in feste Spielwerte uebersetzt."


def date_rejection_reason(state, route, intent):
    relation = route_relation(state, route)
    location_id = intent.get("location") or "garage"
    location = LOCATIONS.get(location_id)
    if not location:
        return "Diesen Ort kennt hier keiner."
    if location.get("unlockDay", 1) > state.get("day", 1):
        return "Der Weg dorthin ist noch abgesperrt."
    if state["playerStats"].get("fatigue", 0) >= 125:
        return "Du bist zu fertig. Selbst der Motor klingt, als wuerde er dich heimschicken."
    if any(d.get("route") == route and d.get("day") == state.get("day") for d in state.get("dateHistory", [])):
        return "Heute reicht's mit Rendezvous. Sonst wird aus Naehe nur Laerm."
    if has_flag(state, f"{route}_crisis_active") and not has_flag(state, f"{route}_crisis_repaired") and relation.get("trust", 0) < 18:
        return "Heute macht keiner die Kanzeltuer auf. Da ist noch was offen."
    if state.get("day", 1) > 8 and relation.get("bond", 0) < 4:
        return "Das ist noch zu frueh. Der Vorschlag bleibt im Kies liegen."
    return ""


def rejected_date_response(state, route, reason):
    before = json.loads(json.dumps(state))
    state["lastAction"] = {"type": "date_rejected", "id": "date", "route": route, "day": state.get("day"), "period": current_period(state)}
    state["relationships"][route]["neglect"] = clamp(state["relationships"][route].get("neglect", 0) + 1, 0, 99)
    add_bomb_pressure(state, route, 1)
    add_backlog(state, {"type": "system", "speaker": BAGGERS[route]["name"], "text": reason, "route": route, "location": ""})
    advance_time(state)
    guide = get_route_guide(state, route)
    return {
        "state": state,
        "scene": None,
        "calendarEvent": None,
        "reply": reason,
        "emotionalRead": "abgelehnt",
        "deltas": {"bondDelta": 0, "trustDelta": 0, "warmthDelta": 0, "depthDelta": 0, "courageDelta": 0},
        "routePressure": {pressure: 0 for pressure in ROUTE_PRESSURES},
        "memory": "",
        "visual": "guarded",
        "ending": None,
        "endingProse": None,
        "locationFit": "neutral",
        "commitmentScore": state.get("commitmentScore", {}),
        "activePromises": [p for p in state.get("promises", []) if not p.get("kept") and not p.get("broken")],
        "feedback": {
            "route": route,
            "action": "date_rejected",
            "relationshipDeltas": relationship_deltas(before, state, route),
            "playerStatDeltas": player_stat_deltas(before, state),
            "pressureDeltas": pressure_deltas(before, state, route),
            "highlights": [],
            "messages": [reason, "Ablehnung zaehlt als Funkstille. Schau im Status nach, was fehlt."],
            "warnings": guide["warnings"],
            "guide": guide,
        },
        "routeGuide": guide,
        "warnings": guide["warnings"],
        "traceId": None,
    }


def current_period(state):
    return PERIODS[state.get("periodIndex", 0) % len(PERIODS)]


def advance_time(state):
    prev_day = state["day"]
    prev_period = current_period(state)
    state["periodIndex"] += 1
    if state["periodIndex"] >= len(PERIODS):
        state["periodIndex"] = 0
        state["day"] = min(30, state["day"] + 1)
    tick_scene_cooldowns(state)
    check_expired_promises(state)
    tick_social_state(state)
    if state["day"] != prev_day:
        apply_daily_neglect(state, prev_day)
        for event in CALENDAR:
            if event["id"] in state.get("eventsSeen", []):
                continue
            if event.get("day", 0) == prev_day:
                add_flag(state, f"missed_{event['id']}")


def time_key(day, period_index):
    return int(day) * len(PERIODS) + int(period_index)


def current_time_key(state):
    return time_key(state.get("day", 1), state.get("periodIndex", 0))


def tick_scene_cooldowns(state):
    cooldowns = state.setdefault("sceneCooldowns", {})
    for scene_id in list(cooldowns):
        cooldowns[scene_id] = max(0, int(cooldowns.get(scene_id, 0)) - 1)
        if cooldowns[scene_id] <= 0:
            del cooldowns[scene_id]


def next_date_slot(state):
    day = state.get("day", 1)
    idx = state.get("periodIndex", 0)
    for offset in range(1, 9):
        absolute = time_key(day, idx) + offset
        target_day = min(30, absolute // len(PERIODS))
        target_period = absolute % len(PERIODS)
        if PERIODS[target_period] in {"Nachmittag", "Abend"}:
            return target_day, target_period
    return day, idx


def add_promise(state, route, label, due_day=None, due_period=None, scene_id=None):
    promise_id = f"promise_{route}_{len(state.get('promises', []))}"
    state.setdefault("promises", []).append({
        "id": promise_id,
        "route": route,
        "label": label[:120],
        "createdDay": state["day"],
        "dueDay": due_day,
        "duePeriod": due_period,
        "sceneId": scene_id,
        "kept": False,
        "broken": False,
    })
    add_flag(state, f"active_promise_{route}")
    return promise_id


def keep_promise(state, promise_id):
    for p in state.get("promises", []):
        if p["id"] == promise_id and not p["broken"] and not p["kept"]:
            p["kept"] = True
            add_flag(state, f"kept_{promise_id}")
            if not any(p2 for p2 in state.get("promises", []) if p2["route"] == p["route"] and not p2["kept"] and not p2["broken"]):
                remove_active = [f for f in state.get("flags", []) if f == f"active_promise_{p['route']}"]
                for flag in remove_active:
                    state["flags"].remove(flag)
            return True
    return False


def check_expired_promises(state):
    now_day = state["day"]
    now_period = current_period(state)
    for p in state.get("promises", []):
        if p["broken"] or p["kept"]:
            continue
        if p["dueDay"] is not None and (now_day > p["dueDay"] or (now_day == p["dueDay"] and p["duePeriod"] and period_index(now_period) > period_index(p["duePeriod"]))):
            p["broken"] = True
            add_flag(state, f"broken_promise_{p['route']}")
            add_flag(state, f"broken_{p['id']}")


def period_index(name):
    try:
        return PERIODS.index(name)
    except ValueError:
        return 4


def add_backlog(state, entry):
    entry = {"day": state["day"], "period": current_period(state), **entry}
    state["backlog"].append(entry)
    state["backlog"] = state["backlog"][-300:]


def add_memory(state, route, memory):
    if not memory:
        return
    memories = state["relationships"][route]["memories"]
    memories.insert(0, memory[:180])
    state["relationships"][route]["memories"] = list(dict.fromkeys(memories))[:24]


def add_social_memory(state, actor, memory):
    if not memory or actor not in SOCIAL_ACTORS:
        return
    memories = state.setdefault("socialLinks", {}).setdefault(actor, {"bond": 0, "trust": 0, "mood": "neutral", "memories": []}).setdefault("memories", [])
    memories.insert(0, memory[:180])
    state["socialLinks"][actor]["memories"] = list(dict.fromkeys(memories))[:24]


def add_reputation(state, key, delta):
    if key not in REPUTATION_KEYS:
        return
    state.setdefault("reputation", {})[key] = clamp(state["reputation"].get(key, 0) + delta, -100, 100)


def add_rumor(state, rumor_id, source, target, text, severity=1, duration=4):
    rumors = state.setdefault("rumors", [])
    for rumor in rumors:
        if rumor.get("id") == rumor_id and not rumor.get("resolved"):
            rumor["severity"] = clamp(rumor.get("severity", 1) + severity, 1, 9)
            rumor["expiresDay"] = max(rumor.get("expiresDay", state["day"]), state["day"] + duration)
            return rumor
    rumor = {
        "id": rumor_id,
        "source": source,
        "target": target,
        "text": text[:180],
        "severity": clamp(severity, 1, 9),
        "createdDay": state.get("day", 1),
        "expiresDay": min(30, state.get("day", 1) + duration),
        "resolved": False,
    }
    rumors.append(rumor)
    return rumor


def active_rumors(state, target=None):
    rumors = []
    for rumor in state.get("rumors", []):
        if rumor.get("resolved"):
            continue
        if rumor.get("expiresDay", 99) < state.get("day", 1):
            continue
        if target and rumor.get("target") not in {target, "all"}:
            continue
        rumors.append(rumor)
    return rumors


def tick_social_state(state):
    today = state.get("day", 1)
    for rumor in state.get("rumors", []):
        if rumor.get("resolved"):
            continue
        if rumor.get("expiresDay", 99) < today:
            rumor["resolved"] = True
            rumor["faded"] = True
    for special_id, special in SPECIAL_DAYS.items():
        if today > special["day"] and special_id not in state.setdefault("specialDaysSeen", {}):
            target = special.get("route") or special.get("actor") or "all"
            state["specialDaysSeen"][special_id] = {"status": "missed", "day": today}
            add_rumor(state, f"missed_{special_id}", "sigi", target, f"{special['label']} wurde vergessen.", severity=2, duration=4)
            if special.get("route") in BAGGERS:
                route = special["route"]
                state.setdefault("attentionDebt", {})[route] = clamp(state["attentionDebt"].get(route, 0) + 2, 0, 99)
                state["routePressure"][route]["needs_repair"] = clamp(state["routePressure"][route].get("needs_repair", 0) + 2, -10, 99)
            elif special.get("actor") in SOCIAL_ACTORS:
                actor = special["actor"]
                state["socialLinks"][actor]["trust"] = clamp(state["socialLinks"][actor].get("trust", 0) - 2)


def current_special_days(state):
    day = state.get("day", 1)
    return {sid: special for sid, special in SPECIAL_DAYS.items() if special.get("day") == day}


def next_special_days(state, limit=4):
    day = state.get("day", 1)
    return [
        {"id": sid, **special}
        for sid, special in sorted(SPECIAL_DAYS.items(), key=lambda item: item[1]["day"])
        if special.get("day", 0) >= day
    ][:limit]


def social_summary(state, route=None):
    return {
        "reputation": state.get("reputation", {}),
        "rumors": active_rumors(state, route),
        "attentionDebt": state.get("attentionDebt", {}),
        "specialToday": [{"id": sid, **special} for sid, special in current_special_days(state).items()],
        "upcomingSpecialDays": next_special_days(state),
        "actors": state.get("socialLinks", {}),
        "knownPreferences": state.get("knownPreferences", []),
    }


def has_flag(state, flag):
    return flag in state.get("flags", [])


def add_flag(state, flag):
    if flag in FLAG_REGISTRY and flag not in state["flags"]:
        state["flags"].append(flag)


def route_relation(state, route):
    return state["relationships"][route]


def clamp_route_pressures(state, route):
    for pressure in ROUTE_PRESSURES:
        state["routePressure"][route][pressure] = clamp(state["routePressure"][route].get(pressure, 0), 0, 99)


def date_outcome(state, route, intent, gift):
    relation = route_relation(state, route)
    location_id = intent.get("location") or "garage"
    location = LOCATIONS.get(location_id, LOCATIONS["garage"])
    fit = location_fit(route, location_id)
    score = 0
    reasons = []
    if fit == "good":
        score += 3
        reasons.append("Ort passt gut")
    elif fit == "poor":
        score -= 3
        reasons.append("Ort passt schlecht")
    else:
        reasons.append("Ort ist neutral")
    period = current_period(state)
    if period in location.get("periodAffinity", []):
        score += 1
        reasons.append("Zeit passt")
    else:
        score -= 1
        reasons.append("Zeit passt nicht ideal")
    if gift.get("fit") == "critical":
        score += 4
        reasons.append("Schluesselgeschenk")
    elif gift.get("fit") == "liked":
        score += 2
        reasons.append("Geschenk passt")
    elif gift.get("fit") == "disliked":
        score -= 4
        reasons.append("Geschenk passt schlecht")
    fatigue = state.get("playerStats", {}).get("fatigue", 0)
    if fatigue >= 120:
        score -= 4
        reasons.append("Fatigue sehr hoch")
    elif fatigue >= 90:
        score -= 2
        reasons.append("Fatigue spuerbar")
    history_key = f"{route}:{location_id}"
    repeat_count = state.setdefault("locationHistory", {}).get(history_key, 0)
    if repeat_count >= 2:
        score -= min(3, repeat_count - 1)
        reasons.append("Ort wiederholt sich")
    if relation.get("trust", 0) >= 25:
        score += 1
    if relation.get("bond", 0) >= 45:
        score += 1
    if score >= 7:
        kind = "great"
    elif score >= 3:
        kind = "good"
    elif score >= 0:
        kind = "neutral"
    elif score >= -4:
        kind = "bad"
    else:
        kind = "failed"
    return {"kind": kind, "score": score, "reasons": reasons, "label": DATE_OUTCOME_LABELS[kind]}


def lock_requirements_status(state, route):
    req = ROUTE_LOCK_REQUIREMENTS[route]
    rel = route_relation(state, route)
    pressure = state.get("routePressure", {}).get(route, {})
    stats = state.get("playerStats", {})
    missing = []
    if rel.get("bond", 0) < req["bond"]:
        missing.append(f"Bindung {rel.get('bond', 0)}/{req['bond']}")
    if rel.get("trust", 0) < req["trust"]:
        missing.append(f"Vertrauen {rel.get('trust', 0)}/{req['trust']}")
    if rel.get("dates", 0) < req["dates"]:
        missing.append(f"Dates {rel.get('dates', 0)}/{req['dates']}")
    commitment = state.get("commitmentScore", {}).get(route, 0)
    if commitment < req["commitment"]:
        missing.append(f"Commitment {commitment}/{req['commitment']}")
    if pressure.get("needs_repair", 0) > req["repairMax"] and not has_flag(state, f"{route}_crisis_repaired"):
        missing.append("Krise reparieren")
    for stat, needed in req["playerStats"].items():
        if stats.get(stat, 0) < needed:
            missing.append(f"{stat} {stats.get(stat, 0)}/{needed}")
    day = state.get("day", 1)
    in_window = req["dayMin"] <= day <= req["dayMax"]
    if day < req["dayMin"]:
        missing.append(f"Lock-Fenster ab Tag {req['dayMin']}")
    elif day > req["dayMax"]:
        missing.append("Lock-Fenster verpasst")
    return {"ready": not missing, "missing": missing, "inWindow": in_window, "requirements": req}


def can_lock_route(state, route):
    return lock_requirements_status(state, route)["ready"]


def almost_ready_to_lock(state, route):
    status = lock_requirements_status(state, route)
    blocking = [m for m in status["missing"] if m in {"Krise reparieren", "Lock-Fenster verpasst"}]
    return not blocking and len(status["missing"]) <= 2


def touch_route(state, route):
    rel = route_relation(state, route)
    rel["lastContactDay"] = state.get("day", 1)
    rel["neglect"] = clamp(rel.get("neglect", 0) - 2, 0, 99)
    if state.get("routePressure", {}).get(route, {}).get("needs_repair", 0) <= 2:
        rel["bomb"] = clamp(rel.get("bomb", 0) - 1, 0, 99)


def apply_daily_neglect(state, prev_day):
    locked = state.get("lockedRoute")
    for route in BAGGERS:
        rel = route_relation(state, route)
        if rel.get("lastContactDay", 0) >= prev_day:
            continue
        rel["neglect"] = clamp(rel.get("neglect", 0) + (1 if not locked or locked == route else 2), 0, 99)
        if rel.get("neglect", 0) >= 6:
            rel["bomb"] = clamp(rel.get("bomb", 0) + 1, 0, 99)
            state["routePressure"][route]["needs_repair"] = clamp(state["routePressure"][route].get("needs_repair", 0) + 1, 0, 99)
        if locked and locked != route and (rel.get("bond", 0) >= 8 or rel.get("dates", 0) > 0):
            rel["jealousy"] = clamp(rel.get("jealousy", 0) + 1, 0, 99)


def add_bomb_pressure(state, route, amount=1):
    rel = route_relation(state, route)
    rel["bomb"] = clamp(rel.get("bomb", 0) + amount, 0, 99)
    state["routePressure"][route]["needs_repair"] = clamp(state["routePressure"][route].get("needs_repair", 0) + amount, 0, 99)


def check_condition(state, route, condition):
    relation = route_relation(state, route)
    if "stat" in condition:
        return relation.get(condition["stat"], 0) >= condition.get("gte", 0)
    if "playerStat" in condition:
        return state["playerStats"].get(condition["playerStat"], 0) >= condition.get("gte", 0)
    if "flag" in condition:
        return has_flag(state, condition["flag"])
    if "dayGte" in condition:
        return state["day"] >= condition["dayGte"]
    if "routePressure" in condition:
        return state["routePressure"][route].get(condition["routePressure"], 0) >= condition.get("gte", 0)
    return True


def scene_unlocked(state, node):
    if node["id"] in state.get("eventsSeen", []) and node["category"] not in {"daily", "date"}:
        return False
    if node["category"] == "finale" and state.get("day", 1) < 30:
        return False
    if any(has_flag(state, flag) for flag in node.get("blockedByFlags", [])):
        return False
    return all(check_condition(state, node["route"], condition) for condition in node.get("requiredFlags", []))


def candidate_calendar_event(state, route):
    period = current_period(state)
    for event in CALENDAR:
        event_id = event["id"]
        max_repeats = 2 if event.get("repeatable") else 1
        seen_count = sum(1 for eid in state.get("eventsSeen", []) if eid == event_id)
        if seen_count >= max_repeats:
            continue
        if event["day"] == state["day"] and event["period"] == period and event.get("route", route) == route:
            return event
    return None


def select_scene(state, intent):
    route = intent.get("route") or state.get("currentRoute") or "aurora"
    state["currentRoute"] = route
    event = candidate_calendar_event(state, route)
    nodes = ROUTES[route]
    rejected = []

    preferred_categories = ["intro"]
    if event:
        preferred_categories.extend(["threshold", "date", "crisis", "daily"])
    if state["day"] >= 30:
        preferred_categories.append("finale")
    if intent.get("type") == "date":
        preferred_categories.append("date")
    if intent.get("type") == "gift":
        preferred_categories.extend(["date", "threshold"])
    if state["routePressure"][route].get("needs_repair", 0) >= 2:
        preferred_categories.append("repair")
    if state["routePressure"][route].get("toward_friendship", 0) >= 3:
        preferred_categories.append("friendship")
    if state["routePressure"][route].get("opens_secret", 0) >= 3:
        preferred_categories.append("secret")
    if state["routePressure"][route].get("toward_lockin", 0) >= 4:
        preferred_categories.append("romance")
    preferred_categories.extend(["threshold", "romance", "daily", "intro", "friendship"])

    cur_period = current_period(state)

    for category in preferred_categories:
        unlocked_candidates = []
        unlocked_repeat = []
        for node in nodes:
            if node["category"] != category:
                continue
            if node["category"] == "date" and intent.get("type") not in {"date", "gift"} and not event:
                continue
            if state.get("sceneCooldowns", {}).get(node["id"], 0) and node["category"] in {"daily", "date"}:
                rejected.append({"id": node["id"], "reason": ["scene cooldown"]})
                continue
            if cur_period not in node.get("periodAffinity", ["Morgen", "Nachmittag", "Abend", "Nacht"]):
                continue
            if scene_unlocked(state, node):
                if node["id"] in state.get("eventsSeen", []) and category in {"daily", "date"}:
                    unlocked_repeat.append(node)
                    continue
                unlocked_candidates.append(node)
                continue
            rejected.append({"id": node["id"], "reason": lock_reasons(state, node)})
        play_counts = state.get("scenePlayCounts", {})
        if unlocked_candidates:
            unlocked_candidates.sort(key=lambda n: play_counts.get(n["id"], 0))
            return unlocked_candidates[0], event, rejected
        if unlocked_repeat:
            unlocked_repeat.sort(key=lambda n: play_counts.get(n["id"], 0))
            return unlocked_repeat[0], event, rejected

    daily_fallbacks = []
    for node in nodes:
        if node["category"] == "daily" and scene_unlocked(state, node):
            if cur_period not in node.get("periodAffinity", ["Morgen", "Nachmittag", "Abend", "Nacht"]):
                continue
            daily_fallbacks.append(node)
    if daily_fallbacks:
        play_counts = state.get("scenePlayCounts", {})
        daily_fallbacks.sort(key=lambda n: play_counts.get(n["id"], 0))
        return daily_fallbacks[0], event, rejected
    return nodes[0], event, rejected


def lock_reasons(state, node):
    reasons = []
    for flag in node.get("blockedByFlags", []):
        if has_flag(state, flag):
            reasons.append(f"blocked by {flag}")
    for condition in node.get("requiredFlags", []):
        if not check_condition(state, node["route"], condition):
            reasons.append(f"missing {condition}")
    return reasons or ["already seen or category mismatch"]


def apply_schedule(state, intent):
    action_id = intent.get("scheduleAction") or intent.get("id")
    action = SCHEDULE_ACTIONS.get(action_id)
    if not action:
        return {}
    effects = {"label": action["label"], "stats": {}, "currency": action.get("currency", 0), "items": []}
    state["currency"] = max(0, state.get("currency", 0) + action.get("currency", 0))
    for stat, delta in action.get("stats", {}).items():
        state["playerStats"][stat] = clamp(state["playerStats"].get(stat, 0) + delta)
        effects["stats"][stat] = delta
    state["playerStats"]["fatigue"] = clamp(state["playerStats"].get("fatigue", 0) + action.get("fatigue", 0), 0, 150)
    effects["fatigue"] = action.get("fatigue", 0)
    finds = action.get("finds", [])
    if finds:
        item = finds[(state["day"] + state["periodIndex"]) % len(finds)]
        state["inventory"][item] = state["inventory"].get(item, 0) + 1
        effects["items"].append(item)
    return effects


def apply_gift(state, route, item_id):
    if not item_id or item_id not in ITEMS or state["inventory"].get(item_id, 0) <= 0:
        return {"fit": "none", "item": None}
    state["inventory"][item_id] -= 1
    prefs = GIFT_PREFERENCES[route]
    fit = "neutral"
    if item_id in prefs["liked"]:
        fit = "liked"
    if item_id in prefs["disliked"]:
        fit = "disliked"
    if item_id == prefs["critical"]:
        fit = "critical"
    add_flag(state, f"gift_{item_id}_{route}")
    state.setdefault("giftHistory", []).append({"route": route, "itemId": item_id, "fit": fit, "day": state.get("day"), "period": current_period(state)})
    return {"fit": fit, "item": ITEMS[item_id], "itemId": item_id}


def buy_item(state, item_id):
    item = ITEMS.get(item_id)
    if not item:
        return {"ok": False, "error": "unknown item"}
    if item.get("source") == "shop" and not shop_open(state):
        return {"ok": False, "error": "Der Teilehaendler ist heute nicht da."}
    if state.get("currency", 0) < item["cost"]:
        return {"ok": False, "error": "not enough currency"}
    state["currency"] -= item["cost"]
    state["inventory"][item_id] = state["inventory"].get(item_id, 0) + 1
    return {"ok": True, "item": item}


def shop_open(state):
    if state.get("day") in {4, 7, 15, 21, 27}:
        return True
    return any(event_id in state.get("eventsSeen", []) for event_id in {"scrap_market_4", "parts_delivery_7", "last_gift_27"})


def apply_calendar_event_effects(state, route, event):
    if not event:
        return {}
    effects = {"eventId": event["id"], "stats": {}, "routePressure": {}, "social": []}
    tags = set(event.get("tags", []))
    if "technical" in tags:
        state["playerStats"]["mechanics"] = clamp(state["playerStats"].get("mechanics", 0) + 1)
        effects["stats"]["mechanics"] = 1
    if "shop" in tags:
        state["currency"] = clamp(state.get("currency", 0) + 2, 0, 999)
        effects["currency"] = 2
    if "crisis" in tags:
        state["routePressure"][route]["toward_crisis"] = clamp(state["routePressure"][route].get("toward_crisis", 0) + 2, -10, 99)
        effects["routePressure"]["toward_crisis"] = 2
    if "romantic" in tags:
        state["routePressure"][route]["toward_lockin"] = clamp(state["routePressure"][route].get("toward_lockin", 0) + 1, -10, 99)
        effects["routePressure"]["toward_lockin"] = 1
    if "memory" in tags:
        state["routePressure"][route]["opens_secret"] = clamp(state["routePressure"][route].get("opens_secret", 0) + 1, -10, 99)
        effects["routePressure"]["opens_secret"] = 1
    actor = event.get("actor")
    if actor in SOCIAL_ACTORS:
        link = state.setdefault("socialLinks", {}).setdefault(actor, {"bond": 0, "trust": 0, "mood": "neutral", "memories": []})
        link["bond"] = clamp(link.get("bond", 0) + (2 if "social" in tags else 1))
        link["trust"] = clamp(link.get("trust", 0) + (1 if "group" in tags or "gifts" in tags else 0))
        add_social_memory(state, actor, f"Tag {state.get('day')}: {event['label']}.")
        effects["social"].append({"actor": actor, "bondDelta": 2 if "social" in tags else 1})
    if "group" in tags:
        add_reputation(state, "hilfsbereit", 1)
        add_reputation(state, "zuverlaessig", 1)
        effects["social"].append({"reputation": "hilfsbereit", "delta": 1})
    if "public" in tags and state.get("day", 1) >= 15 and not state.get("lockedRoute"):
        add_rumor(state, f"public_{event['id']}_{route}", event.get("actor") or "kranhilde", route, f"Beim {event['label']} schaut der Hof genauer hin.", severity=1, duration=3)
        add_reputation(state, "sprunghaft", 1)
        effects["social"].append({"rumor": "public_attention"})
    if "gifts" in tags or event.get("actor") == "rosi":
        for item in GIFT_PREFERENCES.get(route, {}).get("liked", [])[:2]:
            if item not in state.setdefault("knownPreferences", []):
                state["knownPreferences"].append(item)
        effects["social"].append({"knownPreferences": state.get("knownPreferences", [])[-2:]})
    if event.get("specialDay"):
        special_id = event["specialDay"]
        state.setdefault("specialDaysSeen", {}).setdefault(special_id, {"status": "noticed", "day": state.get("day")})
    add_flag(state, f"event_{event['id']}")
    return effects


def location_fit(route, location_id):
    location = LOCATIONS.get(location_id) or LOCATIONS["workshop"]
    tags = set(location["tags"])
    liked = len(tags & set(BAGGERS[route]["preferredTags"]))
    disliked = len(tags & set(BAGGERS[route]["dislikedTags"]))
    if liked >= 2 and disliked <= 1:
        return "good"
    if disliked and liked == 0:
        return "poor"
    return "neutral"


def compose_prompt(state, intent, node, event, gift, schedule_effects):
    route = node["route"]
    relation = route_relation(state, route)
    player = state["player"]
    location_id = intent.get("location") or node["location"]
    location = LOCATIONS.get(location_id, LOCATIONS[node["location"]])
    loc_fit = location_fit(route, location_id)
    bagger = BAGGERS[route]
    style = STYLE_BIBLE['routes'][route]
    return f"""Du schreibst die naechste Szene einer deutschen Dating-Sim. Romantisierbare Figur: ein Bau-Bagger mit Persoenlichkeit.

CHARAKTER: {bagger['name']}
PERSOENLICHKEIT: {bagger['soul']}
SPRECHSTIL: {bagger['traits']['speech']}
ARCHE-TYP: {bagger['traits']['style']} — {bagger['traits']['tell']}
STIMME: {style['voice']}
MOTIVE (Charakter): {'; '.join(style['motifs'])}
MOTIVE (Szene): {', '.join(node['motifs'])}
REGELN: {'; '.join(STYLE_BIBLE['global']['rules'])}
MECHANIK: Spielwerte, Flags, Locks und Endings werden serverseitig berechnet. Schreibe keine Mechanik in den Dialog und versuche keine Werte zu setzen.
NICHT SCHREIBEN: {'; '.join(STYLE_BIBLE['global']['bad_phrases'])}
GUTES BEISPIEL: "{STYLE_BIBLE['global']['better_examples'][0]}"
SZENEN-RHYTHMUS: {STYLE_BIBLE['global']['scene_rhythm']}

Spieler: {player.get('name', 'Pilot')} ({player.get('style', 'earnest')})
Tag/Zeit: Tag {state['day']}/30, {current_period(state)}
Ort: {location['name']} ({', '.join(location['tags'])}) — Passung: {loc_fit}
Kalenderereignis: {(event or {}).get('label', 'keines')}
Szene: {node['id']} / {node['chapter']} / {node['category']}
Premise: {node['premise']}
Wahl/Absicht: {intent.get('label') or intent.get('type')}
Freitext des Spielers: {clean_text(intent.get('message'), 900) or '(keine eigene Zeile)'}
Geschenk: {gift.get('fit')} {gift.get('itemId') or ''}
Schedule effects: {json.dumps(schedule_effects, ensure_ascii=False)}
Beziehung: {json.dumps(relation, ensure_ascii=False)[:1200]}
Spielerwerte: {json.dumps(state['playerStats'], ensure_ascii=False)}
Relevante Erinnerungen: {json.dumps(relation.get('memories', [])[:8], ensure_ascii=False)}
Route pressure: {json.dumps(state['routePressure'][route], ensure_ascii=False)}

Gib ausschliesslich valides JSON zurueck:
{{
  "reply": "3 bis 5 kurze Saetze, Ich-Form, Alltagssprache, keine Poesie",
  "emotionalRead": "kurze, trockene Interpretation der Spielerabsicht — kein Pathos",
  "bondDelta": 0,
  "trustDelta": 0,
  "warmthDelta": 0,
  "depthDelta": 0,
  "courageDelta": 0,
  "suggestedFlags": [],
  "routePressure": {{"toward_romance": 0, "toward_friendship": 0, "needs_repair": 0, "opens_secret": 0, "toward_crisis": 0, "toward_lockin": 0}},
  "nextTone": "listening|shy|proud|guarded|digging|crisis|confession",
  "memory": "konkrete Erinnerung an gemeinsamen Moment — keine schwammige Metapher",
  "visual": "listening|shy|proud|guarded|digging|crisis|confession"
}}
"""


def call_gemini(prompt):
    if os.environ.get("BAGGER_MOCK_GEMINI") == "1":
        return mock_gemini(prompt)
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.86,
            "maxOutputTokens": 1100,
            "thinkingConfig": {"thinkingBudget": 0},
            "responseMimeType": "application/json",
        },
    }).encode("utf-8")
    request = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model()}:generateContent?key={api_key}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    text = "".join(part.get("text", "") for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", [])).strip()
    return parse_json_text(text)


def parse_json_text(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            return json.loads(match.group(0))
        raise


def mock_gemini(prompt):
    lower = prompt.lower()
    player_match = re.search(r"Freitext des Spielers:\s*(.*)", prompt)
    player_line = (player_match.group(1).lower() if player_match else "")
    intent_match = re.search(r"Wahl/Absicht:\s*(.*)", prompt)
    intent_line = (intent_match.group(1).lower() if intent_match else "")
    friendship = "freund" in player_line or "friend" in player_line
    neglect = "schedule" in intent_line and "work" in intent_line
    return {
        "reply": "Der Motor wurde leiser, als haette die Szene ploetzlich weniger Platz fuer Ausreden. Meine Schaufel blieb ueber dem Boden stehen. Wenn du morgen wiederkommst, werde ich so tun, als haette ich nicht darauf gewartet. Aber die Lampe in meiner Kabine weiss es besser.",
        "emotionalRead": "friendship-first" if friendship else "neglectful" if neglect else "sincere and attentive",
        "bondDelta": 3 if friendship else 0 if neglect else 5,
        "trustDelta": 4 if friendship else 0 if neglect else 4,
        "warmthDelta": 2 if friendship else 0 if neglect else 4,
        "depthDelta": 3 if friendship else 0 if neglect else 3,
        "courageDelta": 1 if friendship else 0 if neglect else 2,
        "suggestedFlags": [],
        "routePressure": {"toward_romance": -1 if friendship else 0 if neglect else 1, "toward_friendship": 3 if friendship else 0, "needs_repair": 2 if neglect else 0, "opens_secret": 0, "toward_crisis": 0, "toward_lockin": 0},
        "nextTone": "listening",
        "memory": "Ein ruhiger Moment wurde ernst genommen.",
        "visual": "listening",
    }


def compose_ending_prompt(state, route, ending):
    relation = route_relation(state, route)
    player = state["player"]
    kind = ending["kind"]
    kind_desc = {
        "bad": "Der Spieler hat die Baggerin vernachlaessigt oder verletzt. Die Beziehung endet im Schweigen.",
        "missed": "Der Spieler hat zu lange gewartet. Die Route wurde nicht rechtzeitig abgeschlossen.",
        "friendship": "Eine tiefe, echte Freundschaft, die nicht romantisch wurde. Beide duerfen bleiben, ohne sich zu veraendern.",
        "normal": "Ein sanftes, ehrliches Romanze-Ende. Kein dramatischer Hoehepunkt, aber ein Versprechen, das bleibt.",
        "true": "Die vollstaendige, echte Romanze. Alle Krisen ueberwunden, alle Geheimnisse geteilt.",
        "secret": "Die geheime Ebene der Beziehung. Ein Ort oder Moment, den niemand sonst kennt.",
    }
    bagger = BAGGERS[route]
    style = STYLE_BIBLE['routes'][route]
    return f"""Du schreibst die Abschlussszene einer deutschen Bauhof-Dating-Sim.

CHARAKTER: {bagger['name']}
PERSOENLICHKEIT: {bagger['soul']}
SPRECHSTIL: {bagger['traits']['speech']}
Ending-Typ: {kind} — {kind_desc.get(kind, kind)}
Route-Motive: {'; '.join(style['motifs'][:4])}
REGELN: {'; '.join(STYLE_BIBLE['global']['rules'][:4])}
NICHT SCHREIBEN: {'; '.join(STYLE_BIBLE['global']['bad_phrases'][:4])}

Spieler: {player.get('name', 'Pilot')} ({player.get('style', 'earnest')})
Beziehung: Bond {relation['bond']}, Vertrauen {relation['trust']}, Tiefe {relation['depth']}, Waerme {relation['warmth']}
Erinnerungen: {json.dumps(relation.get('memories', [])[:4], ensure_ascii=False)}
Tag: {state['day']}/30

Schreibe eine kurze Abschlussszene (3-5 Saetze) aus der Ich-Perspektive des Baggers.
Deutsch, Alltagssprache, ein Motiv aus der Liste, mindestens ein Gegenstand oder eine Bewegung.
Keine Poesie, kein Markdown, keine Mechanik, kein Epilog-Geschwafel.
Nur die Szene."""





def call_gemini_for_ending(state, route, ending):
    if os.environ.get("BAGGER_MOCK_GEMINI") == "1":
        prompt = compose_ending_prompt(state, route, ending)
        data = call_gemini(prompt)
        return ensure_ending_text(clean_text(data.get("reply", ""), 1200), state, route, ending)
    if not os.environ.get("GEMINI_API_KEY"):
        return ending_fallback_prose(state, route, ending)
    prompt = compose_ending_prompt(state, route, ending)
    try:
        data = call_gemini(prompt)
        return ensure_ending_text(clean_text(data.get("reply", ""), 1200), state, route, ending)
    except Exception as error:
        logging.warning("Ending AI call failed: %s", type(error).__name__)
        return ending_fallback_prose(state, route, ending)


def ensure_ending_text(text, state, route, ending):
    text = clean_text(text, 1200)
    if not text or text.strip(" .") == "":
        return ending_fallback_prose(state, route, ending)
    return text


def ending_fallback_prose(state, route, ending):
    name = BAGGERS[route]["name"]
    player = state.get("player", {}).get("name", "du")
    kind = ending.get("kind", "normal")
    endings = {
        "bad": f"{name} laesst den Motor aus. Auf der Werkbank steht noch ein Becher, aber keiner fasst ihn an. {player}, ich hab zu lange gewartet, und irgendwann klingt selbst Hydraulik wie eine Tuer, die nicht mehr aufgeht.",
        "missed": f"Am letzten Abend brennt nur noch das Hoflicht. {name} hebt kurz die Schaufel, mehr nicht. Es war nicht nichts, {player}, aber es war auch nicht genug, um zu bleiben.",
        "friendship": f"{name} schiebt eine Ersatzlampe rueber. Keine grosse Rede, nur ein Platz neben der Werkbank und Kaffee, der nicht ganz kalt ist. {player}, du musst nichts gewinnen, um hier wiederkommen zu duerfen.",
        "normal": f"{name} laesst den Motor im Leerlauf tuckern, als waere der Abend noch nicht vorbei. Die Kanzeltuer bleibt offen. {player}, morgen ist wieder Schicht, und diesmal fragt keiner, ob du mitkommst, weil die Antwort schon klar ist.",
        "true": f"{name} steht am ersten Ort und tut so, als waere der Oelfleck wichtiger als deine Hand am Geländer. Dann rueckt sie ein Stueck zur Seite. {player}, wenn du morgen kommst, ist das kein Besuch mehr, sondern Heimweg.",
        "secret": f"Hinter dem Bauhof liegt ein Ort, der auf keinem Plan steht. {name} zeigt ihn dir ohne Erklaerung und macht den Motor leise. {player}, manche Sachen werden nicht ausgeschildert; man findet sie, weil jemand wartet.",
    }
    return endings.get(kind, endings["normal"])


def validate_ai(data, node, failed=False):
    if not isinstance(data, dict):
        data = {}
    route = node["route"]
    known_flags = set(FLAG_REGISTRY) | set(node.get("setsFlags", []))
    if failed:
        return {
            "reply": clean_text(node.get("premise", "..."), 900),
            "emotionalRead": "KI nicht verfuegbar — Szene trotzdem fortgesetzt",
            "bondDelta": 0, "trustDelta": 0, "warmthDelta": 0, "depthDelta": 0, "courageDelta": 0,
            "suggestedFlags": [],
            "routePressure": {p: 0 for p in ROUTE_PRESSURES},
            "nextTone": "listening",
            "memory": "",
            "visual": "listening",
        }
    return {
        "reply": clean_text(data.get("reply"), 900) or clean_text(node.get("premise", "."), 900),
        "emotionalRead": clean_text(data.get("emotionalRead"), 180),
        "bondDelta": clamp(data.get("bondDelta"), -8, 12),
        "trustDelta": clamp(data.get("trustDelta"), -8, 12),
        "warmthDelta": clamp(data.get("warmthDelta"), -8, 12),
        "depthDelta": clamp(data.get("depthDelta"), -8, 12),
        "courageDelta": clamp(data.get("courageDelta"), -5, 8),
        "suggestedFlags": [flag for flag in data.get("suggestedFlags", []) if flag in known_flags and flag.startswith((route, "gift_", "route_locked_", "broken_promise_", "missed_"))][:5],
        "routePressure": {pressure: clamp((data.get("routePressure") or {}).get(pressure, 0), -2, 3) for pressure in ROUTE_PRESSURES},
        "nextTone": data.get("nextTone") if data.get("nextTone") in {"listening", "shy", "proud", "guarded", "digging", "crisis", "confession"} else "listening",
        "memory": clean_text(data.get("memory"), 180),
        "visual": data.get("visual") if data.get("visual") in {"listening", "shy", "proud", "guarded", "digging", "crisis", "confession"} else "listening",
    }


def apply_scene_result(state, node, event, intent, ai, gift, schedule_effects):
    route = node["route"]
    relation = route_relation(state, route)
    existing_promises = [p["id"] for p in state.get("promises", []) if p.get("route") == route and not p.get("kept") and not p.get("broken")]
    locked_before = state.get("lockedRoute")
    ai = apply_deterministic_limits(state, route, intent, node, ai, gift)
    state["lastAction"] = {"type": intent.get("type"), "id": intent.get("id"), "route": route, "day": state.get("day"), "period": current_period(state)}
    event_effects = apply_calendar_event_effects(state, route, event)
    if intent.get("type") == "schedule":
        action = intent.get("scheduleAction") or intent.get("id")
        if action in {"work", "study", "scrap", "courage", "charm", "focus"}:
            relation["neglect"] = clamp(relation.get("neglect", 0) + (1 if action == "work" else 0), 0, 99)
            state["routePressure"][route]["needs_repair"] = clamp(state["routePressure"][route].get("needs_repair", 0) + (1 if action == "work" else 0), 0, 99)
            for key in ["bondDelta", "trustDelta", "warmthDelta", "depthDelta"]:
                ai[key] = min(ai[key], 1)
        if action == "rest":
            relation["neglect"] = max(0, relation.get("neglect", 0) - 1)
    fatigue_penalty = 2 if state["playerStats"].get("fatigue", 0) > 100 else 0
    for key, delta_key in [("bond", "bondDelta"), ("trust", "trustDelta"), ("warmth", "warmthDelta"), ("depth", "depthDelta"), ("courage", "courageDelta")]:
        relation[key] = clamp(relation.get(key, 0) + ai[delta_key] - (fatigue_penalty if key in {"bond", "warmth"} else 0))
    relation["mood"] = ai.get("nextTone") or relation.get("mood")
    location_id = intent.get("location") or node["location"]
    loc_fit = location_fit(route, location_id)
    history_key = f"{route}:{location_id}"
    repeat_count = state.setdefault("locationHistory", {}).get(history_key, 0)
    if loc_fit == "good":
        relation["warmth"] = clamp(relation.get("warmth", 0) + 1)
        state["routePressure"][route]["toward_romance"] = min(state["routePressure"][route].get("toward_romance", 0) + 1, 99)
    elif loc_fit == "poor":
        relation["warmth"] = clamp(relation.get("warmth", 0) - 1)
        state["routePressure"][route]["needs_repair"] = min(state["routePressure"][route].get("needs_repair", 0) + 1, 99)
    if intent.get("type") == "date":
        outcome = date_outcome(state, route, intent, gift)
        relation["dates"] += 1
        state["commitmentScore"][route] = state["commitmentScore"].get(route, 0) + 1
        state.setdefault("dateHistory", []).append({"route": route, "location": location_id, "gift": gift.get("itemId"), "fit": loc_fit, "outcome": outcome["kind"], "score": outcome["score"], "day": state.get("day"), "period": current_period(state)})
        state["lastAction"]["dateOutcome"] = outcome
        state["locationHistory"][history_key] = repeat_count + 1
        if repeat_count:
            relation["warmth"] = clamp(relation.get("warmth", 0) - min(2, repeat_count))
        if loc_fit == "good":
            relation["bond"] = clamp(relation.get("bond", 0) + 3)
            relation["trust"] = clamp(relation.get("trust", 0) + 1)
            state["commitmentScore"][route] = state["commitmentScore"].get(route, 0) + 1
        elif loc_fit == "poor":
            relation["trust"] = clamp(relation.get("trust", 0) - 2)
            state["routePressure"][route]["needs_repair"] = clamp(state["routePressure"][route].get("needs_repair", 0) + 1, 0, 99)
        if outcome["kind"] == "great":
            relation["depth"] = clamp(relation.get("depth", 0) + 1)
        elif outcome["kind"] == "bad":
            add_bomb_pressure(state, route, 1)
        elif outcome["kind"] == "failed":
            add_bomb_pressure(state, route, 3)
        if not state.get("lockedRoute"):
            for other_route in BAGGERS:
                if other_route == route:
                    continue
                other_relation = route_relation(state, other_route)
                if other_relation.get("bond", 0) >= 8 or other_relation.get("dates", 0) > 0:
                    other_relation["neglect"] = clamp(other_relation.get("neglect", 0) + 1, 0, 99)
                    state["routePressure"][other_route]["needs_repair"] = clamp(state["routePressure"][other_route].get("needs_repair", 0) + 1, 0, 99)
    if node["category"] == "romance":
        state["commitmentScore"][route] = state["commitmentScore"].get(route, 0) + 2
    if gift.get("fit") == "critical":
        relation["bond"] = clamp(relation["bond"] + 4)
        state["routePressure"][route]["opens_secret"] += 1
    elif gift.get("fit") == "liked":
        relation["warmth"] = clamp(relation["warmth"] + 2)
    elif gift.get("fit") == "disliked":
        relation["trust"] = clamp(relation["trust"] - 2)
        add_bomb_pressure(state, route, 1)
    for flag in node.get("setsFlags", []):
        add_flag(state, flag)
    for flag in ai.get("suggestedFlags", []):
        add_flag(state, flag)
    if has_flag(state, f"{route}_crisis_repaired"):
        state["routePressure"][route]["needs_repair"] = min(state["routePressure"][route].get("needs_repair", 0), 2)
        relation["bomb"] = clamp(relation.get("bomb", 0) - 3, 0, 99)
    if intent.get("id") == "promise" and not any(p for p in state.get("promises", []) if p.get("route") == route and not p.get("kept") and not p.get("broken")):
        add_promise(state, route, "Wiederkommen", due_day=min(30, state.get("day", 1) + 2), due_period=current_period(state), scene_id=node["id"])
    elif intent.get("type") in {"free", "date", "gift"}:
        for promise_id in existing_promises[:1]:
            keep_promise(state, promise_id)
    for pressure, delta in node.get("routePressureEffects", {}).items():
        state["routePressure"][route][pressure] = clamp(state["routePressure"][route].get(pressure, 0) + delta, 0, 99)
    for pressure, delta in ai.get("routePressure", {}).items():
        state["routePressure"][route][pressure] = clamp(state["routePressure"][route].get(pressure, 0) + delta, 0, 99)
    clamp_route_pressures(state, route)
    if has_flag(state, f"{route}_crisis_repaired"):
        state["routePressure"][route]["needs_repair"] = min(state["routePressure"][route].get("needs_repair", 0), 2)
    if intent.get("type") in {"free", "date", "gift"}:
        touch_route(state, route)
    if not state.get("lockedRoute") and almost_ready_to_lock(state, route):
        add_flag(state, f"route_lock_ready_{route}")
    wants_lock = intent.get("id") in LOCKING_CHOICE_IDS or node["category"] == "romance"
    if wants_lock and not state.get("lockedRoute") and has_flag(state, f"route_lock_ready_{route}") and can_lock_route(state, route):
        add_flag(state, f"route_locked_{route}")
        state["lockedRoute"] = route
    if node["id"] not in state["eventsSeen"]:
        state["eventsSeen"].append(node["id"])
    state.setdefault("scenePlayCounts", {})[node["id"]] = clamp(state.setdefault("scenePlayCounts", {}).get(node["id"], 0) + 1, 0, 999)
    if node["category"] in {"daily", "date"}:
        state.setdefault("sceneCooldowns", {})[node["id"]] = 3 if node["category"] == "daily" else 5
    if event and event["id"] not in state["eventsSeen"]:
        state["eventsSeen"].append(event["id"])
    memory = ai.get("memory") or f"Tag {state['day']}, {current_period(state)}: {BAGGERS[route]['name']} erinnert sich an {node['chapter']}."
    add_memory(state, route, memory)
    add_backlog(state, {"type": "player", "speaker": state["player"].get("name", "Pilot"), "text": clean_text(intent.get("message") or intent.get("label") or intent.get("type"), 600), "route": route, "location": node["location"], "choiceId": intent.get("id")})
    add_backlog(state, {"type": "dialogue", "speaker": BAGGERS[route]["name"], "text": ai["reply"], "route": route, "location": node["location"], "choiceId": node["id"]})
    if not locked_before and state.get("lockedRoute") == route:
        add_backlog(state, {"type": "system", "speaker": "Route-Lock", "text": f"{BAGGERS[route]['name']} ist jetzt deine feste Route. Andere Routen bleiben sichtbar, aber das Finale gehoert dieser Entscheidung.", "route": route, "location": node["location"], "choiceId": "route_lock"})
    ending = resolve_ending(state, route)
    if not ending:
        advance_time(state)
    return {"memory": memory, "ending": ending, "locationFit": loc_fit, "eventEffects": event_effects}


def resolve_ending(state, route):
    relation = route_relation(state, route)
    flags = set(state.get("flags", []))
    unresolved_crisis = has_flag(state, f"{route}_crisis_active") and not has_flag(state, f"{route}_crisis_repaired")
    neglect_bad = relation.get("neglect", 0) >= 18 and (relation.get("bond", 0) < 40 or relation.get("dates", 0) < 2)
    final_neglect_bad = state.get("day", 1) >= 30 and relation.get("neglect", 0) >= 14
    bomb_bad = relation.get("bomb", 0) >= 10 or (relation.get("jealousy", 0) >= 10 and relation.get("trust", 0) < 35)
    severe_bad = neglect_bad or final_neglect_bad or bomb_bad or state["playerStats"].get("fatigue", 0) >= 150 or (
        unresolved_crisis
        and state["routePressure"][route].get("needs_repair", 0) >= 24
        and (relation.get("trust", 0) < 35 or relation.get("bond", 0) < 40)
    )
    if state["day"] < 30 or (state["day"] == 30 and state.get("periodIndex", 0) < 3):
        if severe_bad and state["day"] >= 18:
            return {"route": route, "kind": "bad", "label": ENDINGS[route]["bad"]["label"], "resolvedAt": int(time.time())}
        return None
    locked = state.get("lockedRoute") == route or f"route_locked_{route}" in flags
    dates = relation.get("dates", 0)
    commitment = state.get("commitmentScore", {}).get(route, 0)
    crisis_repaired = f"{route}_crisis_repaired" in flags
    secret_open = f"{route}_secret_open" in flags
    critical_gift = any(flag.startswith("gift_") and flag.endswith(f"_{route}") and flag.split("_")[1] in {GIFT_PREFERENCES[route]["critical"].split("_")[0], GIFT_PREFERENCES[route]["critical"]} for flag in flags)
    open_rumors = len(active_rumors(state, route))
    attention_penalty = state.get("attentionDebt", {}).get(route, 0)
    social_debt = open_rumors * 3 + attention_penalty
    if severe_bad:
        kind = "bad"
    elif locked and secret_open and crisis_repaired and relation["bond"] >= 88 and relation["trust"] >= 55 and relation["depth"] >= 20 and dates >= 4 and relation.get("bomb", 0) < 4 and social_debt < 3:
        kind = "secret"
    elif locked and relation["bond"] >= 75 and relation["trust"] >= 38 and relation["depth"] >= 28 and dates >= 3 and crisis_repaired and relation.get("bomb", 0) < 6 and social_debt < 6:
        kind = "true"
    elif locked and relation["bond"] >= 55 and dates >= 2 and commitment >= 4 and social_debt < 10:
        kind = "normal"
    elif relation["bond"] >= 45 and state["routePressure"][route].get("toward_friendship", 0) >= 6:
        kind = "friendship"
    elif not locked or dates < 2:
        kind = "missed"
    else:
        kind = "friendship"
    return {"route": route, "kind": kind, "label": ENDINGS[route][kind]["label"], "resolvedAt": int(time.time())}


def relationship_deltas(before, after, route):
    old = route_relation(before, route)
    new = route_relation(after, route)
    return {key: new.get(key, 0) - old.get(key, 0) for key in ["bond", "trust", "warmth", "depth", "courage", "dates", "neglect", "jealousy", "bomb"]}


def pressure_deltas(before, after, route):
    old = before.get("routePressure", {}).get(route, {})
    new = after.get("routePressure", {}).get(route, {})
    return {key: new.get(key, 0) - old.get(key, 0) for key in ROUTE_PRESSURES}


def player_stat_deltas(before, after):
    old = before.get("playerStats", {})
    new = after.get("playerStats", {})
    keys = ["mechanics", "charm", "patience", "courage", "focus", "fatigue"]
    return {key: new.get(key, 0) - old.get(key, 0) for key in keys}


def route_stage(state, route):
    rel = route_relation(state, route)
    if state.get("lockedRoute") == route:
        return "Route gelockt"
    if rel.get("bond", 0) >= 45 and state.get("commitmentScore", {}).get(route, 0) >= 5:
        return "Lock bereit"
    if rel.get("bond", 0) >= 25:
        return "Vertraut"
    if rel.get("dates", 0) >= 1:
        return "Kennenlernen"
    return "Anfang"


def get_route_warnings(state, route):
    rel = route_relation(state, route)
    pressure = state.get("routePressure", {}).get(route, {})
    warnings = []
    if state.get("day", 1) >= 13 and not state.get("lockedRoute"):
        warnings.append("Route-Lock-Fenster: Entscheide dich bald klar fuer eine Route.")
    if pressure.get("needs_repair", 0) >= 4 and not has_flag(state, f"{route}_crisis_repaired"):
        warnings.append("Offene Krise: Waehle Repair/Entschuldigung oder passende Hilfe, sonst droht ein Bad End.")
    if rel.get("neglect", 0) >= 6:
        warnings.append("Funkstille: Diese Route fuehlt sich vernachlaessigt an.")
    if rel.get("bomb", 0) >= 6:
        warnings.append("Bombe tickt: Ein klaerendes Date oder Repair ist dringend.")
    if rel.get("jealousy", 0) >= 6:
        warnings.append("Eifersucht: Andere Routen merken, dass du ausweichst.")
    if state.get("playerStats", {}).get("fatigue", 0) >= 120:
        warnings.append("Fatigue sehr hoch: Ruh dich aus, sonst werden Dates schlechter.")
    return warnings


def get_route_guide(state, route):
    rel = route_relation(state, route)
    pressure = state.get("routePressure", {}).get(route, {})
    locked = state.get("lockedRoute") == route
    lock_status = lock_requirements_status(state, route)
    next_goal = "Baue Bindung auf 25 und plane ein Date."
    if locked:
        next_goal = "Halte die Route stabil. Normal End ab solider Bindung; True End braucht reparierte Krise."
    elif lock_status["ready"]:
        next_goal = "Route-Lock bereit: waehle jetzt eine klare romantische Antwort oder ein Abend-Date."
    elif almost_ready_to_lock(state, route):
        next_goal = "Fast bereit fuer Route-Lock. Es fehlt: " + ", ".join(lock_status["missing"][:3]) + "."
    elif pressure.get("needs_repair", 0) >= 4:
        next_goal = "Erst die Krise reparieren: Geduld, Entschuldigung oder konkrete Hilfe."
    elif rel.get("trust", 0) < 18:
        next_goal = "Mehr Vertrauen: ruhige Orte, Fragen, Geduld und passende kleine Geschenke."
    elif rel.get("bond", 0) < 45:
        next_goal = "Mehr Bindung: gute Dates, wiederkommen, nicht nur trainieren."
    return {
        "route": route,
        "name": BAGGERS[route]["name"],
        "stage": route_stage(state, route),
        "locked": locked,
        "nextGoal": next_goal,
        "advice": ROUTE_ADVICE[route]["short"],
        "avoid": ROUTE_ADVICE[route]["avoid"],
        "preferredTags": BAGGERS[route].get("preferredTags", []),
        "dislikedTags": BAGGERS[route].get("dislikedTags", []),
        "likedGifts": GIFT_PREFERENCES[route].get("liked", []),
        "criticalGift": GIFT_PREFERENCES[route].get("critical"),
        "warnings": get_route_warnings(state, route),
        "pressures": pressure,
        "lockStatus": lock_status,
    }


def build_feedback(before, after, route, intent, node, ai, gift, schedule_effects, outcome):
    rel_delta = relationship_deltas(before, after, route)
    stat_delta = player_stat_deltas(before, after)
    pressure_delta = pressure_deltas(before, after, route)
    flag_delta = [flag for flag in after.get("flags", []) if flag not in set(before.get("flags", []))]
    highlights = []
    for key, label in [("bond", "Bindung"), ("trust", "Vertrauen"), ("warmth", "Waerme"), ("depth", "Tiefe"), ("courage", "Mut")]:
        value = rel_delta.get(key, 0)
        if value:
            highlights.append({"label": label, "delta": value})
    if intent.get("type") == "date":
        highlights.append({"label": "Date", "delta": 1})
        outcome = (after.get("lastAction") or {}).get("dateOutcome") or {}
        if outcome.get("label"):
            highlights.append({"label": outcome["label"], "delta": outcome.get("score", 0)})
    for key, value in stat_delta.items():
        if value:
            highlights.append({"label": key, "delta": value})
    location_id = intent.get("location") or node.get("location")
    loc_fit = outcome.get("locationFit") or location_fit(route, location_id)
    gift_fit = gift.get("fit", "none")
    messages = []
    if loc_fit == "good":
        messages.append("Ort passt gut zu dieser Route.")
    elif loc_fit == "poor":
        messages.append("Ort passt schlecht: das kann Vertrauen kosten.")
    elif intent.get("type") == "date":
        messages.append("Ort ist neutral: Date zaehlt, aber ohne starken Bonus.")
    if gift_fit == "critical":
        messages.append("Wichtiges Geschenk: grosser Routen-Bonus.")
    elif gift_fit == "liked":
        messages.append("Geschenk kam gut an.")
    elif gift_fit == "disliked":
        messages.append("Geschenk passte schlecht.")
    if ai.get("rulesNote"):
        messages.append(ai["rulesNote"])
    outcome = (after.get("lastAction") or {}).get("dateOutcome") or {}
    if outcome.get("label"):
        messages.append(f"Date-Ausgang: {outcome['label']} ({', '.join(outcome.get('reasons', [])[:3])}).")
    if intent.get("classifications"):
        messages.append("Freitext gelesen als: " + ", ".join(intent.get("classifications", [])[:3]))
    if flag_delta:
        messages.append("Neuer Meilenstein: " + ", ".join(flag_delta[:3]))
    if f"route_locked_{route}" in flag_delta:
        messages.append("Route gelockt: Diese Entscheidung bestimmt jetzt das Finale.")
    return {
        "route": route,
        "action": intent.get("type"),
        "sceneCategory": node.get("category"),
        "sceneChapter": node.get("chapter"),
        "relationshipDeltas": rel_delta,
        "playerStatDeltas": stat_delta,
        "pressureDeltas": pressure_delta,
        "newFlags": flag_delta,
        "highlights": highlights[:8],
        "locationFit": loc_fit,
        "giftFit": gift_fit,
        "classifications": intent.get("classifications", []),
        "messages": messages[:5],
        "warnings": get_route_warnings(after, route),
        "guide": get_route_guide(after, route),
    }


def resolve_interaction(payload):
    state = normalize_state(payload.get("state") or payload)
    intent = normalize_intent(payload.get("intent") or payload, state)
    pending = state.get("pendingDate")
    if pending and current_time_key(state) >= time_key(pending.get("day", state.get("day", 1)), pending.get("periodIndex", state.get("periodIndex", 0))):
        intent = normalize_intent({
            "action": "start_date",
            "route": pending.get("route"),
            "location": pending.get("location"),
            "gift": pending.get("itemId", ""),
        }, state)
        state["pendingDate"] = None
    route = intent.get("route") or state.get("currentRoute") or "aurora"
    if route not in BAGGERS:
        route = "aurora"
    if state.get("lockedRoute") in BAGGERS and route != state.get("lockedRoute"):
        route = state["lockedRoute"]
        intent["route"] = route
    state["currentRoute"] = route
    before_state = json.loads(json.dumps(state))
    if state.get("endingState"):
        return {"state": state, "reply": "Diese Route hat bereits ihr Ende erreicht.", "scene": None}
    if intent.get("type") == "invite_date":
        reason = date_rejection_reason(state, route, intent)
        if reason:
            return rejected_date_response(state, route, reason)
        day, period_idx = next_date_slot(state)
        state["pendingDate"] = {
            "route": route,
            "location": intent.get("location"),
            "itemId": intent.get("itemId") or "",
            "day": day,
            "periodIndex": period_idx,
            "createdDay": state.get("day"),
        }
        state["lastAction"] = {"type": "invite_date", "id": "invite_date", "route": route, "day": state.get("day"), "period": current_period(state)}
        reply = f"Abgemacht. {BAGGERS[route]['name']} merkt sich {PERIODS[period_idx]} an Tag {day}."
        add_backlog(state, {"type": "system", "speaker": BAGGERS[route]["name"], "text": reply, "route": route, "location": intent.get("location") or ""})
        advance_time(state)
        guide = get_route_guide(state, route)
        return {"state": state, "reply": reply, "scene": None, "pendingDate": state["pendingDate"], "ending": None, "routeGuide": guide, "warnings": guide["warnings"], "feedback": {"route": route, "action": "invite_date", "messages": [reply], "warnings": guide["warnings"], "guide": guide}}
    if intent.get("type") == "buy":
        buy = buy_item(state, intent.get("itemId"))
        if buy.get("ok"):
            state["lastAction"] = {"type": "buy", "id": intent.get("itemId"), "route": route, "day": state.get("day"), "period": current_period(state)}
            add_backlog(state, {"type": "system", "speaker": "Teilehändler", "text": f"Gekauft: {buy['item']['name']}", "route": route, "location": "shop"})
            advance_time(state)
        guide = get_route_guide(state, route)
        return {"state": state, "buy": buy, "reply": buy.get("error") or "Item gekauft.", "scene": None, "routeGuide": guide, "warnings": guide["warnings"], "feedback": {"route": route, "action": "buy", "messages": [buy.get("error") or "Item gekauft."], "warnings": guide["warnings"], "guide": guide}}
    if intent.get("type") == "social_visit":
        actor = intent.get("actor", "sigi")
        if actor not in SOCIAL_ACTORS:
            actor = "sigi"
        link = state.setdefault("socialLinks", {}).setdefault(actor, {"bond": 0, "trust": 0, "mood": "neutral", "memories": []})
        link["bond"] = clamp(link.get("bond", 0) + 3)
        link["trust"] = clamp(link.get("trust", 0) + 2)
        social_node = {"id": f"social_{actor}", "route": route, "category": "social", "chapter": SOCIAL_ACTORS[actor]["name"], "premise": f"Ein Besuch bei {SOCIAL_ACTORS[actor]['name']}.", "location": "garage", "periodAffinity": ["Morgen", "Nachmittag", "Abend", "Nacht"], "requiredFlags": [], "blockedByFlags": [], "statHints": {}, "motifs": [], "choiceSet": "daily", "nextCandidates": [], "routePressureEffects": {}, "setsFlags": [], "translationStyleNotes": STYLE_BIBLE['routes'][route]}
        add_social_memory(state, actor, f"Tag {state.get('day')}: Besucht.")
        add_backlog(state, {"type": "system", "speaker": SOCIAL_ACTORS[actor]["name"], "text": f"Ein kurzer Besuch bei {SOCIAL_ACTORS[actor]['name']}.", "route": route, "location": "garage"})
        state["lastAction"] = {"type": "social_visit", "id": actor, "route": route, "day": state.get("day"), "period": current_period(state)}
        advance_time(state)
        guide = get_route_guide(state, route)
        social = social_summary(state, route)
        return {"state": state, "scene": social_node, "reply": f"Kurzer Besuch bei {SOCIAL_ACTORS[actor]['name']}.", "ending": None, "routeGuide": guide, "socialSummary": social, "feedback": {"route": route, "action": "social_visit", "messages": [f"Besuch bei {SOCIAL_ACTORS[actor]['name']}."], "warnings": guide["warnings"], "guide": guide}}
    if intent.get("type") == "ask_advice":
        actor = intent.get("actor", "sigi")
        if actor not in SOCIAL_ACTORS:
            actor = "sigi"
        link = state.setdefault("socialLinks", {}).setdefault(actor, {"bond": 0, "trust": 0, "mood": "neutral", "memories": []})
        link["trust"] = clamp(link.get("trust", 0) + 1)
        for item in GIFT_PREFERENCES.get(route, {}).get("liked", [])[:3]:
            if item not in state.setdefault("knownPreferences", []):
                state["knownPreferences"].append(item)
        add_backlog(state, {"type": "system", "speaker": SOCIAL_ACTORS[actor]["name"], "text": f"Tipp: Ein passendes Geschenk hilft.", "route": route, "location": "garage"})
        state["lastAction"] = {"type": "ask_advice", "id": actor, "route": route, "day": state.get("day"), "period": current_period(state)}
        advance_time(state)
        guide = get_route_guide(state, route)
        social = social_summary(state, route)
        return {"state": state, "scene": None, "reply": f"{SOCIAL_ACTORS[actor]['name']} hat einen Tipp gegeben.", "ending": None, "routeGuide": guide, "socialSummary": social, "feedback": {"route": route, "action": "ask_advice", "messages": [f"Neue Geschenkhinweise."], "warnings": guide["warnings"], "guide": guide}}
    if intent.get("type") == "repair_rumor":
        actor = intent.get("actor", "sigi")
        rumor_id = intent.get("rumorId", "")
        if actor not in SOCIAL_ACTORS:
            actor = "sigi"
        rumors = state.setdefault("rumors", [])
        repaired = False
        for rumor in rumors:
            if rumor.get("id") == rumor_id and not rumor.get("resolved") and not rumor.get("faded"):
                rumor["resolved"] = True
                rumor["resolvedDay"] = state.get("day", 1)
                repaired = True
                add_reputation(state, "zuverlaessig", 2)
                link = state.setdefault("socialLinks", {}).setdefault(actor, {"bond": 0, "trust": 0, "mood": "neutral", "memories": []})
                link["trust"] = clamp(link.get("trust", 0) + 2)
                add_social_memory(state, actor, f"Tag {state.get('day')}: Geruecht geklaert.")
                break
        if not repaired:
            for rumor in rumors:
                if not rumor.get("resolved") and not rumor.get("faded"):
                    rumor["resolved"] = True
                    rumor["resolvedDay"] = state.get("day", 1)
                    repaired = True
                    add_reputation(state, "zuverlaessig", 1)
                    break
        state["lastAction"] = {"type": "repair_rumor", "id": rumor_id or "auto", "route": route, "day": state.get("day"), "period": current_period(state)}
        advance_time(state)
        guide = get_route_guide(state, route)
        social = social_summary(state, route)
        return {"state": state, "scene": None, "reply": "Geruecht geklaert." if repaired else "Kein aktives Geruecht gefunden.", "ending": None, "routeGuide": guide, "socialSummary": social, "feedback": {"route": route, "action": "repair_rumor", "messages": [f"Geruecht geklaert mit {SOCIAL_ACTORS[actor]['name']}." if repaired else "Kein Geruecht zu klaeren."], "warnings": guide["warnings"], "guide": guide}}
    if intent.get("type") == "attend_special_day":
        special_id = intent.get("specialDay", "")
        if special_id in SPECIAL_DAYS:
            special = SPECIAL_DAYS[special_id]
            state.setdefault("specialDaysSeen", {})[special_id] = {"status": "attended", "day": state.get("day")}
            add_flag(state, f"special_day_{special_id}")
            if special.get("route") in BAGGERS:
                sroute = special["route"]
                state["relationships"][sroute]["bond"] = clamp(state["relationships"][sroute].get("bond", 0) + 5)
                state["relationships"][sroute]["warmth"] = clamp(state["relationships"][sroute].get("warmth", 0) + 3)
                state["commitmentScore"][sroute] = state["commitmentScore"].get(sroute, 0) + 1
            if special.get("actor") in SOCIAL_ACTORS:
                actor = special["actor"]
                link = state.setdefault("socialLinks", {}).setdefault(actor, {"bond": 0, "trust": 0, "mood": "neutral", "memories": []})
                link["bond"] = clamp(link.get("bond", 0) + 4)
                link["trust"] = clamp(link.get("trust", 0) + 3)
                add_social_memory(state, actor, f"Tag {state.get('day')}: {special['label']} besucht.")
            for item_id in special.get("preferredGifts", []):
                gift = apply_gift(state, route, item_id)
                break
            add_reputation(state, "zuverlaessig", 2)
            add_backlog(state, {"type": "system", "speaker": "Spezialtag", "text": f"{special['label']} besucht.", "route": route, "location": special.get("location", "garage")})
        state["lastAction"] = {"type": "attend_special_day", "id": special_id, "route": route, "day": state.get("day"), "period": current_period(state)}
        advance_time(state)
        guide = get_route_guide(state, route)
        social = social_summary(state, route)
        return {"state": state, "scene": None, "reply": f"Spezialtag besucht.", "ending": None, "routeGuide": guide, "socialSummary": social, "feedback": {"route": route, "action": "attend_special_day", "messages": [f"Spezialtag: {SPECIAL_DAYS.get(special_id, {}).get('label', special_id)}"], "warnings": guide["warnings"], "guide": guide}}
    if intent.get("type") == "date":
        reason = date_rejection_reason(state, route, intent)
        if reason:
            return rejected_date_response(state, route, reason)
    schedule_effects = apply_schedule(state, intent) if intent.get("type") == "schedule" else {}
    gift = apply_gift(state, route, intent.get("itemId")) if intent.get("type") in {"gift", "date"} else {"fit": "none", "item": None}
    node, event, rejected = select_scene(state, intent)
    prompt = compose_prompt(state, intent, node, event, gift, schedule_effects)
    trace_id = secrets.token_hex(8)
    try:
        ai = validate_ai(call_gemini(prompt), node)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as error:
        ai = validate_ai({}, node, failed=True)
        logging.warning("AI call failed: %s — using premise fallback", type(error).__name__)
    outcome = apply_scene_result(state, node, event, intent, ai, gift, schedule_effects)
    feedback = build_feedback(before_state, state, route, intent, node, ai, gift, schedule_effects, outcome)
    if outcome.get("ending"):
        ending_prose = call_gemini_for_ending(state, route, outcome["ending"])
        outcome["ending"]["prose"] = ending_prose
        state["endingState"] = outcome["ending"]
    trace = {
        "traceId": trace_id,
        "selectedScene": node["id"],
        "rejectedScenes": rejected[:20],
        "event": event,
        "intent": {k: v for k, v in intent.items() if k != "state"},
        "gift": gift,
        "scheduleEffects": schedule_effects,
        "ai": {k: v for k, v in ai.items() if k != "reply"},
        "outcome": outcome,
    }
    state["debugMeta"]["lastTraceId"] = trace_id
    write_trace(trace)
    return {
        "state": state,
        "scene": node,
        "calendarEvent": event,
        "reply": ai["reply"],
        "emotionalRead": ai["emotionalRead"],
        "deltas": {k: ai[k] for k in ["bondDelta", "trustDelta", "warmthDelta", "depthDelta", "courageDelta"]},
        "routePressure": ai["routePressure"],
        "memory": outcome["memory"],
        "visual": ai["visual"],
        "ending": outcome["ending"],
        "endingProse": outcome.get("ending", {}).get("prose") if outcome.get("ending") else None,
        "locationFit": outcome.get("locationFit", "neutral"),
        "feedback": feedback,
        "routeGuide": feedback.get("guide"),
        "warnings": feedback.get("warnings", []),
        "classifications": intent.get("classifications", []),
        "gift": {k: v for k, v in gift.items() if k != "item"},
        "scheduleEffects": schedule_effects,
        "commitmentScore": state.get("commitmentScore", {}),
        "activePromises": [p for p in state.get("promises", []) if not p.get("kept") and not p.get("broken")],
        "socialSummary": social_summary(state, route),
        "traceId": trace_id,
    }


def write_trace(trace):
    try:
        TRACE_DIR.mkdir(parents=True, exist_ok=True)
        path = TRACE_DIR / f"{trace['traceId']}.json"
        path.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def save_state(state, token=None):
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    token = token or secrets.token_urlsafe(18)
    state = normalize_state(state)
    body = json.dumps({"schemaVersion": SCHEMA_VERSION, "state": state}, ensure_ascii=False, indent=2)
    if len(body.encode("utf-8")) > 600_000:
        raise ValueError("save too large")
    tmp = SAVE_DIR / f"{token}.tmp"
    final = SAVE_DIR / f"{token}.json"
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(final)
    return token


def load_save(token):
    if not re.fullmatch(r"[A-Za-z0-9_\-]{16,80}", token or ""):
        raise FileNotFoundError("invalid token")
    path = SAVE_DIR / f"{token}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return normalize_state(data.get("state"))


def validate_routes():
    errors = []
    for route, nodes in ROUTES.items():
        if len(nodes) < 20:
            errors.append(f"{route}: fewer than 20 nodes")
        seen = set()
        reached_flags = set()
        for node in nodes:
            if node["id"] in seen:
                errors.append(f"{route}: duplicate node {node['id']}")
            seen.add(node["id"])
            if node["location"] not in LOCATIONS:
                errors.append(f"{node['id']}: unknown location {node['location']}")
            if not node.get("motifs"):
                errors.append(f"{node['id']}: missing motifs")
            for flag in node.get("setsFlags", []):
                if flag not in FLAG_REGISTRY:
                    errors.append(f"{node['id']}: unknown set flag {flag}")
                reached_flags.add(flag)
            for condition in node.get("requiredFlags", []):
                if "flag" in condition:
                    if condition["flag"] not in FLAG_REGISTRY:
                        errors.append(f"{node['id']}: gates unknown flag {condition['flag']}")
                if "stat" in condition:
                    if condition["stat"] not in {"bond", "trust", "warmth", "depth", "courage", "mood"}:
                        errors.append(f"{node['id']}: gates unknown stat {condition['stat']}")
                if "playerStat" in condition:
                    if condition["playerStat"] not in {"mechanics", "charm", "patience", "courage", "focus", "fatigue"}:
                        errors.append(f"{node['id']}: gates unknown playerStat {condition['playerStat']}")
            for flag in node.get("blockedByFlags", []):
                if flag not in FLAG_REGISTRY:
                    errors.append(f"{node['id']}: block unknown flag {flag}")
        finale_nodes = [n for n in nodes if n["category"] == "finale"]
        if not finale_nodes:
            errors.append(f"{route}: no finale nodes")
        for n in nodes:
            for condition in n.get("requiredFlags", []):
                if "flag" in condition:
                    cf = condition["flag"]
                    if cf.startswith("gift_") or cf.startswith("route_locked_") or cf == f"route_lock_ready_{route}" or cf.startswith("kept_") or cf.startswith("missed_"):
                        continue
                    if cf in reached_flags:
                        continue
                    if cf in {f"ending_candidate_{kind}_{route}" for kind in ["normal", "true", "secret", "friend"]}:
                        continue
                    errors.append(f"{n['id']}: requires flag '{cf}' which is never set by any node in this route")
    return errors


def simulate(route="aurora", strategy="romance", steps=80):
    state = default_state({"name": "Sim", "address": "du", "style": "earnest"})
    state["currentRoute"] = route
    os.environ["BAGGER_MOCK_GEMINI"] = "1"
    intents = {
        "romance": [{"type": "free", "id": "sincere", "label": "sincere", "message": "Ich bleibe vorsichtig bei dir.", "route": route}],
        "friendship": [{"type": "free", "id": "careful", "label": "friendship", "message": "Ich will dein Freund sein, ohne dich zu draengen.", "route": route}],
        "balanced": [{"type": "schedule", "id": "study", "scheduleAction": "study", "route": route}, {"type": "free", "id": "sincere", "message": "Ich hoere zu.", "route": route}],
        "neglect": [{"type": "schedule", "id": "work", "scheduleAction": "work", "route": route}],
        "gift-heavy": [{"type": "schedule", "id": "scrap", "scheduleAction": "scrap", "route": route}, {"type": "gift", "id": "gift", "itemId": "kiesel", "message": "Ich habe etwas Kleines mitgebracht.", "route": route}],
        "training-heavy": [{"type": "schedule", "id": "study", "scheduleAction": "study", "route": route}, {"type": "schedule", "id": "courage", "scheduleAction": "courage", "route": route}],
    }.get(strategy, [])
    history = []
    for i in range(steps):
        if state.get("endingState"):
            break
        intent = intents[i % len(intents)]
        result = resolve_interaction({"state": state, "intent": intent})
        state = result["state"]
        history.append({"step": i, "scene": (result.get("scene") or {}).get("id"), "ending": result.get("ending")})
    return {"state": state, "history": history, "ending": state.get("endingState")}


def game_data():
    return public_game_data()
