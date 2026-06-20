#!/usr/bin/env python3
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)
os.environ.setdefault("BAGGER_MOCK_GEMINI", "1")

from game_engine import default_state, resolve_interaction, validate_routes, current_special_days, add_flag  # noqa: E402
from game_data import SPECIAL_DAYS, SOCIAL_ACTORS  # noqa: E402


GOOD_LOCATIONS = {
    "aurora": ["workshop", "garage", "observatory", "hill_road"],
    "brummbert": ["workshop", "garage", "old_tunnel", "rain_shelter"],
    "mira": ["workshop", "garage", "riverbed", "quarry_edge"],
}


def step_until_end(route, chooser, limit=170):
    state = default_state({"name": "QA", "address": "du", "style": "earnest"})
    state["currentRoute"] = route
    history = []
    for step in range(limit):
        if state.get("endingState"):
            break
        intent = chooser(route, state, step)
        result = resolve_interaction({"state": state, "intent": intent})
        state = result["state"]
        if result.get("ending"):
            state["endingState"] = result["ending"]
            break
        history.append({"step": step, "scene": (result.get("scene") or {}).get("id"), "ending": result.get("ending")})
    return state, history


def focused_romance(route, state, step):
    ps = state["playerStats"]
    rel = state["relationships"][route]
    pressure = state["routePressure"][route]
    flags = set(state["flags"])
    if ps["fatigue"] > 125:
        return {"action": "schedule", "activity": "rest", "route": route}
    if ps["mechanics"] < 6:
        return {"action": "schedule", "activity": "study", "route": route}
    if route == "aurora" and ps["patience"] < 12:
        return {"action": "schedule", "activity": "focus", "route": route}
    if route == "brummbert":
        if ps["courage"] < 8:
            return {"action": "schedule", "activity": "courage", "route": route}
        if ps["patience"] < 5:
            return {"action": "schedule", "activity": "focus", "route": route}
    if route == "mira" and ps["focus"] < 18:
        return {"action": "schedule", "activity": "focus", "route": route}
    if route in {"brummbert", "mira"} and ps["mechanics"] < 12:
        return {"action": "schedule", "activity": "study", "route": route}
    if pressure.get("needs_repair", 0) >= 4 and f"{route}_crisis_repaired" not in flags:
        return {"action": "advance", "choice": "action", "route": route}
    if state.get("lockedRoute") == route or rel.get("bond", 0) >= 40:
        return {"action": "advance", "choice": "choose", "route": route}
    return {"action": "start_date", "route": route, "location": GOOD_LOCATIONS[route][step % len(GOOD_LOCATIONS[route])], "gift": ""}


def social_savvy(route, state, step):
    """Focused romance player who also maintains social fabric: visits NPCs, repairs rumors, attends special days."""
    ps = state["playerStats"]
    rel = state["relationships"][route]
    pressure = state["routePressure"][route]
    flags = set(state["flags"])
    day = state.get("day", 1)

    # Rest if tired
    if ps["fatigue"] > 125:
        return {"action": "schedule", "activity": "rest", "route": route}

    # Train stats
    if ps["mechanics"] < 6:
        return {"action": "schedule", "activity": "study", "route": route}
    if route == "aurora" and ps["patience"] < 12:
        return {"action": "schedule", "activity": "focus", "route": route}
    if route == "brummbert":
        if ps["courage"] < 8:
            return {"action": "schedule", "activity": "courage", "route": route}
        if ps["patience"] < 5:
            return {"action": "schedule", "activity": "focus", "route": route}
    if route == "mira" and ps["focus"] < 18:
        return {"action": "schedule", "activity": "focus", "route": route}
    if route in {"brummbert", "mira"} and ps["mechanics"] < 12:
        return {"action": "schedule", "activity": "study", "route": route}

    # Attend special days when they occur
    special_today = current_special_days(state)
    if special_today:
        sid = next(iter(special_today))
        if sid not in state.get("specialDaysSeen", {}):
            return {"action": "attend_special_day", "specialDayId": sid, "route": route}

    # Repair rumors periodically
    active = [r for r in state.get("rumors", []) if not r.get("resolved")]
    if active and step % 15 == 7:
        actor = active[0].get("source", "sigi")
        if actor in SOCIAL_ACTORS:
            return {"action": "repair_rumor", "rumorIndex": 0, "socialActorId": actor, "route": route}

    # Visit NPCs to maintain social bonds
    if step > 20 and step % 12 == 3:
        npc_id = list(SOCIAL_ACTORS.keys())[step % len(SOCIAL_ACTORS)]
        return {"action": "social_visit", "socialActorId": npc_id, "route": route}

    # Repair route
    if pressure.get("needs_repair", 0) >= 4 and f"{route}_crisis_repaired" not in flags:
        return {"action": "advance", "choice": "action", "route": route}

    # Advance or date
    if state.get("lockedRoute") == route or rel.get("bond", 0) >= 40:
        return {"action": "advance", "choice": "choose", "route": route}
    return {"action": "start_date", "route": route, "location": GOOD_LOCATIONS[route][step % len(GOOD_LOCATIONS[route])], "gift": ""}


def chaotic_multi(route, _state, step):
    """Dates every route, ignores social fabric — should accumulate social debt and end badly."""
    routes = ["aurora", "brummbert", "mira"]
    r = routes[step % 3]
    locs = ["garage", "workshop", "scrapyard"]
    return {"action": "start_date", "route": r, "location": locs[step % 3], "gift": ""}


def neglect(route, _state, _step):
    return {"action": "schedule", "activity": "work", "route": route}


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    errors = validate_routes()
    assert_true(not errors, "Route validation failed: " + "; ".join(errors))

    # Standard focused runs
    for route in ["aurora", "brummbert", "mira"]:
        state, _history = step_until_end(route, focused_romance)
        ending = state.get("endingState") or {}
        assert_true(ending.get("kind") in {"normal", "true", "secret"}, f"{route}: focused play should win, got {ending}")
        assert_true(state.get("lockedRoute") == route, f"{route}: focused play should lock route")
        assert_true(state["relationships"][route].get("dates", 0) >= 2, f"{route}: focused play should include dates")
        print(f"PASS focused {route}: {ending.get('kind')}")

    # Social-savvy runs — should achieve good ending with low social debt
    for route in ["aurora", "brummbert", "mira"]:
        state, _history = step_until_end(route, social_savvy)
        ending = state.get("endingState") or {}
        assert_true(ending.get("kind") in {"normal", "true", "secret"}, f"{route}: social-savvy play should win, got {ending}")
        ad = state.get("attentionDebt", {}).get(route, 0)
        assert_true(ad < 6, f"{route}: social-savvy should keep attentionDebt < 6, got {ad}")
        attended = len([v for v in state.get("specialDaysSeen", {}).values() if v.get("status") == "attended"])
        assert_true(attended >= 2, f"{route}: social-savvy should attend >= 2 special days, got {attended}")
        assert_true(state.get("lockedRoute") == route, f"{route}: social-savvy should lock route")
        print(f"PASS social-savvy {route}: {ending.get('kind')} (debt={ad}, attended={attended})")

    # Chaotic multi-dating — should end badly with high social debt
    state, _history = step_until_end("aurora", chaotic_multi, limit=170)
    ending = state.get("endingState") or {}
    assert_true(ending.get("kind") in {"bad", "missed", "friendship"}, f"chaotic multi should lose, got {ending}")
    rumors = len([r for r in state.get("rumors", []) if not r.get("resolved")])
    print(f"PASS chaotic multi: {ending.get('kind')} (rumors={rumors})")

    # Neglect
    state, _history = step_until_end("aurora", neglect)
    ending = state.get("endingState") or {}
    assert_true(ending.get("kind") in {"bad", "missed"}, f"neglect should lose, got {ending}")
    print(f"PASS neglect aurora: {ending.get('kind')}")


if __name__ == "__main__":
    main()
