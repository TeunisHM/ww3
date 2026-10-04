"""Small, deterministic balance experiments in explicitly synthetic scenarios.

Run from the repository root: .venv/bin/python -m tools.probe_balance
These isolate incentives; they are not ordinary campaign outcomes.
"""

import json

from ww3.core.catalog import FACTIONS, FRONTS
from ww3.core.engine import new_game, resolve_round


def empty_fronts():
    game = new_game(mode="sandbox")
    for faction in FACTIONS:
        game.nations[faction].deployments = dict.fromkeys(FRONTS, 0.0)
        game.orders[faction].deployments = dict.fromkeys(FRONTS, 0.0)
    return game


def run_probes():
    empty = resolve_round(empty_fronts())
    garrison = empty_fronts()
    garrison.orders["US"].deployments = dict.fromkeys(FRONTS, .01)
    tiny = resolve_round(garrison)
    presence = {
        "setup": "All other forces withdrawn; US deploys 0.01 power on each front.",
        "total_deployed": .04,
        "additional_dominance_income": tiny.nations["US"].last_ledger["dominance_income"] - empty.nations["US"].last_ledger["dominance_income"],
        "deployment_upkeep": -tiny.nations["US"].last_ledger["military_upkeep"],
        "influence_gained": tiny.influence("US") - garrison.influence("US"),
    }
    breakthroughs = []
    for power in (1200, 1202):
        game = empty_fronts()
        game.nations["EU"].military = game.nations["EU"].military_capacity = power
        game.orders["EU"].deployments[FRONTS[0]] = power
        game.orders["Russia"].deployments[FRONTS[0]] = 100
        result = resolve_round(game)
        breakthroughs.append({"eu_power": power, "russian_power": 100,
            "russian_survivors": result.nations["Russia"].deployments[FRONTS[0]],
            "eu_influence_gain": result.fronts[FRONTS[0]].influence["EU"] - game.fronts[FRONTS[0]].influence["EU"],
            "status": result.fronts[FRONTS[0]].status})
    recovery = []
    for committed in (0, 300):
        game = empty_fronts()
        game.nations["US"].military = 300
        game.nations["US"].military_capacity = 400
        game.orders["US"].deployments[FRONTS[2]] = committed
        result = resolve_round(game)
        production = result.nations["US"].last_production
        recovery.append({"military_before_orders": 300, "deployed": committed,
            "new_military": production["military"], "reserve_recovery": production["reserve_recovery"]})
    return {"synthetic_scenarios": True, "rules_changed": False,
        "token_garrison": presence, "russian_breakthrough": breakthroughs,
        "recovery_with_fresh_production": recovery}


if __name__ == "__main__":
    print(json.dumps(run_probes(), indent=2))
