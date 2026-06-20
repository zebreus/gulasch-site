#!/usr/bin/env python3
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)
os.environ.setdefault("BAGGER_MOCK_GEMINI", "1")

from game_data import ROUTES, public_game_data  # noqa: E402
from game_engine import default_state, load_save, resolve_ending, select_scene, simulate, validate_routes  # noqa: E402


def print_json(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def list_routes(_args):
    print_json({route: len(nodes) for route, nodes in ROUTES.items()})


def show_route(args):
    print_json(ROUTES.get(args.route, []))


def validate(_args):
    errors = validate_routes()
    print_json({"ok": not errors, "errors": errors})
    return 1 if errors else 0


def run_simulation(args):
    print_json(simulate(args.route, args.strategy, args.steps))


def ending_fixture(args):
    state = default_state({"name": "Fixture", "style": "earnest", "address": "du"})
    route = args.fixture.split("_", 1)[-1] if "_" in args.fixture else args.route
    kind = args.fixture.split("_", 1)[0]
    state["currentRoute"] = route
    state["lockedRoute"] = route
    state["day"] = 30
    state["periodIndex"] = 3
    state["relationships"][route].update({"bond": 95, "trust": 80, "warmth": 80, "depth": 80, "courage": 60})
    state["flags"].append(f"route_locked_{route}")
    if kind in {"normal", "true", "secret", "friend"}:
        state["flags"].append(f"ending_candidate_{'friend' if kind == 'friend' else kind}_{route}")
    print_json({"fixture": args.fixture, "ending": resolve_ending(state, route), "state": state})


def explain_scene(args):
    state = load_save(args.save) if args.save else default_state()
    if args.route:
        state["currentRoute"] = args.route
    node, event, rejected = select_scene(state, {"type": args.intent, "route": state["currentRoute"]})
    print_json({"selected": node, "calendarEvent": event, "rejected": rejected[:50]})


def dump_data(_args):
    print_json(public_game_data())


def main():
    parser = argparse.ArgumentParser(description="Bagger Hearts route simulation and debug CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-routes").set_defaults(func=list_routes)
    show = sub.add_parser("show-route")
    show.add_argument("route")
    show.set_defaults(func=show_route)
    sub.add_parser("validate-routes").set_defaults(func=validate)
    data = sub.add_parser("dump-data")
    data.set_defaults(func=dump_data)

    sim = sub.add_parser("simulate")
    sim.add_argument("--route", default="aurora")
    sim.add_argument("--strategy", default="romance", choices=["romance", "friendship", "balanced", "neglect", "gift-heavy", "training-heavy"])
    sim.add_argument("--steps", type=int, default=80)
    sim.set_defaults(func=run_simulation)

    fixture = sub.add_parser("ending-fixture")
    fixture.add_argument("fixture")
    fixture.add_argument("--route", default="aurora")
    fixture.set_defaults(func=ending_fixture)

    explain = sub.add_parser("explain-scene")
    explain.add_argument("--save", default="")
    explain.add_argument("--route", default="")
    explain.add_argument("--intent", default="free")
    explain.set_defaults(func=explain_scene)

    args = parser.parse_args()
    result = args.func(args)
    raise SystemExit(result or 0)


if __name__ == "__main__":
    main()
