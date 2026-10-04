"""A non-mutating preview using the exact same rules as end-year resolution."""

from copy import copy
from ww3.core.ai import prepare_ai_orders
from ww3.core.catalog import FACTIONS, FRONTS
from ww3.core.construction import construction_rows
from ww3.core.engine import _prepare, resolve_round
from ww3.core.models import Game
from ww3.core.strategy import objective_progress, theater_snapshot

RESOURCES = {
    "currency": "Treasury · T USD", "energy": "Energy · PJ", "minerals": "Minerals · t",
    "compute": "Available compute", "productivity": "Productivity",
    "innovation": "Innovation", "military": "Military power", "gdp": "GDP · T USD",
    "content": "Citizen content", "debt": "Debt · T USD",
}


def forecast_round(game: Game) -> dict:
    candidate = copy(game)
    candidate.history, candidate.reports = [], []
    candidate = prepare_ai_orders(candidate)
    committed, messages, _ = _prepare(candidate)
    resolved = resolve_round(candidate)
    forecasts = {}
    for f in FACTIONS:
        rows = []
        for resource, label in RESOURCES.items():
            opening = game.debt(f) if resource == "debt" else getattr(game.nations[f], resource)
            after_orders = committed.debt(f) if resource == "debt" else getattr(committed.nations[f], resource)
            if resource == "productivity":
                after_orders -= sum(candidate.orders[f].investments.values())
            closing = resolved.debt(f) if resource == "debt" else getattr(resolved.nations[f], resource)
            rows.append({"key": resource, "resource": label, "current": opening,
                "after_orders": after_orders, "system_change": closing - after_orders,
                "expected": closing, "change": closing - opening})
        forecasts[f] = {"resources": rows, "ledger": resolved.nations[f].last_ledger,
            "production": resolved.nations[f].last_production,
            "construction": construction_rows(candidate, f, committed, messages)}
    return {"round": game.round, "year": game.year, "mode": game.mode, "factions": forecasts,
        "fronts": {name: {"planned": theater_snapshot(committed, name), "expected": theater_snapshot(resolved, name)} for name in FRONTS},
        "objectives": {f: objective_progress(resolved, f) for f in FACTIONS},
        "streaks": dict(resolved.objective_streaks)}
