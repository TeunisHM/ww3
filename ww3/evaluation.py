"""Reproducible campaign diagnostics; observation limits are not game turn caps.

python -m ww3.evaluation run --output /tmp/ww3-baseline --seeds 17 23 --turns 30
python -m ww3.evaluation replay /tmp/ww3-baseline/EU-factory-17
"""

import argparse
from collections import Counter
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from .ai import FRONT_WEIGHTS, prepare_ai_orders, prepare_computer_orders
from .catalog import FACTIONS, FRONTS
from .engine import InvalidOrder, fresh_order, investment_cost, new_game, preview_plan, resolve_round
from .models import Order, RULES_VERSION
from .persistence import dumps, loads
from .rules import Rules
from .strategy import objective_progress

POLICIES = {
    "current": "Existing computer policy for all four factions",
    "factory": "Factory expansion with supply repairs; usual front weights",
    "military": "Drone/modernization investment; concentrate 80% on the primary front",
    "research": "Research labs/programs with supply repairs; usual front weights",
    "cooperation": "Offer agreements and shared benefits, zero tariffs, outreach and civic/infrastructure investment",
    "objective": "Support military production and forecast allocations across the faction's complete objectives",
    "objective-industry": "Objective policy with a larger early factory investment before sustained military production",
}


def state_hash(game):
    return sha256(json.dumps(game.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def policy_fingerprint():
    digest = sha256()
    for name in ("ai.py", "catalog.py", "engine.py", "evaluation.py", "objective_policy.py", "models.py", "persistence.py", "reporting.py", "rules.py", "strategy.py"):
        digest.update(name.encode())
        digest.update(Path(__file__).with_name(name).read_bytes())
    return digest.hexdigest()


def scripted_orders(game, policy):
    if policy not in POLICIES:
        raise ValueError(f"Unknown evaluation policy: {policy}")
    if game.mode != "solo":
        raise ValueError("Campaign evaluations use solo scenarios.")
    if policy == "current":
        return prepare_computer_orders(game, FACTIONS)
    if policy in ("objective", "objective-industry"):
        from .objective_policy import prepare_objective_orders
        return prepare_objective_orders(game, industrial=policy == "objective-industry")
    work = deepcopy(game)
    f, n = work.player, work.nations[work.player]
    order = fresh_order(work, f)
    work.orders[f] = order
    weights = FRONT_WEIGHTS[f]
    primary = max(range(len(FRONTS)), key=lambda i: weights[i])
    budget = int(n.military * .8)
    order.deployments = dict.fromkeys(FRONTS, 0.0) if policy == "military" else {
        name: float(int(budget * weight / sum(weights))) for name, weight in zip(FRONTS, weights)}
    order.deployments[FRONTS[primary]] += budget - sum(order.deployments.values())
    if policy == "cooperation":
        peers = [other for other in FACTIONS if other != f]
        order.trade_offers = list(peers)
        order.alliance_offers = list(peers)
        order.share_bonus = list(peers) if f in ("US", "China") else []
        order.tariffs = dict.fromkeys(peers, 0.0)
        if n.currency > work.rules.diplomacy_cost + .5:
            targets = [other for other in peers if n.relations[other] < 4.7]
            if targets:
                order.improve_relations = [max(targets, key=lambda other: n.relations[other])]
    # Opponents see the policy's real treaty/deployment choices. Construction
    # does not alter their policy inputs until the year actually resolves.
    work = prepare_ai_orders(work)
    order = work.orders[f]
    preferences = {
        "factory": ["factory"], "military": ["drone", "modernization", "cyber"],
        "research": ["research", "research_grant"],
        "cooperation": ["civil_investment", "infrastructure", "factory"],
    }[policy]
    for _ in range(40):
        remaining = n.productivity - sum(order.investments.values())
        if remaining < 1:
            break
        repairs = []
        if n.last_production.get("energy_supply", 1) < .98 or n.energy < 12:
            repairs += ["renewable", "thermal"]
        if n.last_production.get("compute_supply", 1) < .98:
            repairs += ["datacenter"]
        if n.minerals < 6:
            repairs += ["mine"]
        for investment in dict.fromkeys(repairs + preferences + ["datacenter", "mine", "renewable"]):
            previous = order.investments.get(investment, 0.0)
            order.investments[investment] = previous + min(remaining, investment_cost(work, f, investment)["productivity"])
            try:
                preview = preview_plan(work, f)
                if preview["currency"] < min(.5, n.gdp * .03):
                    raise InvalidOrder("Preserve reserves")
            except InvalidOrder:
                if previous:
                    order.investments[investment] = previous
                else:
                    order.investments.pop(investment)
            else:
                break
        else:
            break
    return work


def metrics(game, faction):
    n = game.nations[faction]
    return {"currency": n.currency, "gdp": n.gdp, "debt": game.debt(faction),
        "energy": n.energy, "minerals": n.minerals, "compute": n.compute,
        "productivity": n.productivity, "military": n.military,
        "innovation": n.innovation, "content": n.content, "influence": game.influence(faction),
        "objective_streak": game.objective_streaks[faction],
        "objective_conditions_met": sum(item["met"] for item in objective_progress(game, faction)),
        "objectives": objective_progress(game, faction),
        "buildings": dict(n.buildings), "deployments": dict(n.deployments),
        "operating_balance": n.last_ledger.get("operating_balance", 0.0)}


def run_campaign(player="EU", policy="current", seed=17, turns=30, *, directory=None, initial=None):
    if type(turns) is not int or not 1 <= turns <= 250:
        raise ValueError("Use an observation window of 1–250 years.")
    if policy not in POLICIES:
        raise ValueError("Unknown evaluation policy.")
    game = deepcopy(initial) if initial is not None else new_game(player=player, rules=Rules(ai_seed=seed))
    if game.mode != "solo" or game.winners:
        raise ValueError("Start from a solo scenario before its first victory.")
    start_round = game.round
    if directory is not None:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=False)  # Never overwrite an earlier experiment.
        (directory / "initial.json").write_text(dumps(game))
    stats = {f: {"shortage_years": 0, "objective_starts": 0, "objective_resets": 0,
        "maximum_objective_conditions_met": 0, "maximum_objective_streak": 0,
        "new_borrowing": 0.0, "unused_productivity": 0.0, "minimum_currency": game.nations[f].currency,
        "maximum_debt": game.debt(f), "investment_productivity": {}, "first_objective_streak_round": None} for f in FACTIONS}
    records = []
    transcript = (directory / "orders.jsonl").open("w") if directory is not None else None
    try:
        for _ in range(turns):
            prepared = scripted_orders(game, policy)
            resolved = resolve_round(prepared)
            for f in FACTIONS:
                values, nation = stats[f], resolved.nations[f]
                old, new = game.objective_streaks[f], resolved.objective_streaks[f]
                values["objective_starts"] += int(old == 0 and new > 0)
                values["objective_resets"] += int(old > 0 and new == 0)
                values["maximum_objective_conditions_met"] = max(values["maximum_objective_conditions_met"],
                    sum(row["met"] for row in objective_progress(resolved, f)))
                values["maximum_objective_streak"] = max(values["maximum_objective_streak"], new)
                if new and values["first_objective_streak_round"] is None:
                    values["first_objective_streak_round"] = game.round
                values["shortage_years"] += int(min(nation.last_production[k] for k in ("energy_supply", "compute_supply", "thermal_supply")) < 1 - 1e-8)
                values["new_borrowing"] += nation.last_ledger["new_borrowing"]
                values["unused_productivity"] += max(0, game.nations[f].productivity - sum(prepared.orders[f].investments.values()))
                values["minimum_currency"] = min(values["minimum_currency"], nation.currency)
                values["maximum_debt"] = max(values["maximum_debt"], resolved.debt(f))
                for key, points in prepared.orders[f].investments.items():
                    values["investment_productivity"][key] = values["investment_productivity"].get(key, 0) + points
            record = {"round": game.round, "orders": {f: asdict(order) for f, order in prepared.orders.items()},
                "after_hash": state_hash(resolved), "metrics": {f: metrics(resolved, f) for f in FACTIONS}}
            if transcript:
                transcript.write(json.dumps(record, separators=(",", ":"), allow_nan=False) + "\n")
                transcript.flush()
            records.append(record)
            game = resolved
            if game.winners:
                break
    finally:
        if transcript:
            transcript.close()
    summary = {"player": game.player, "policy": policy, "seed": game.rules.ai_seed, "rules_version": RULES_VERSION,
        "start_round": start_round, "observation_limit_years": turns, "years_resolved": game.round - start_round,
        "winners": list(game.winners), "first_victory_round": game.round - 1 if game.winners else None,
        "stop_reason": "victory" if game.winners else "observation_limit", "final_hash": state_hash(game),
        "by_faction": {f: {**stats[f], "end": metrics(game, f)} for f in FACTIONS}}
    if directory is not None:
        # Validate the final portable artifact before calling the run complete.
        payload = dumps(game)
        loads(payload)
        (directory / "final.json").write_text(payload)
        (directory / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    return summary, records


def replay_campaign(directory):
    directory = Path(directory)
    game = loads((directory / "initial.json").read_bytes())
    expected = json.loads((directory / "summary.json").read_text())
    count = 0
    with (directory / "orders.jsonl").open() as stream:
        for line in stream:
            record = json.loads(line)
            if record["round"] != game.round or set(record["orders"]) != set(FACTIONS):
                raise ValueError("Replay has a missing, duplicated or out-of-order year.")
            try:
                game.orders = {f: Order(**order) for f, order in record["orders"].items()}
                game = resolve_round(game)  # Recorded orders, never reroll/replan the AI.
            except (TypeError, KeyError) as exc:
                raise ValueError("Malformed recorded orders.") from exc
            if state_hash(game) != record["after_hash"]:
                raise ValueError(f"Replay diverged after round {record['round']}.")
            count += 1
    final = loads((directory / "final.json").read_bytes())
    if count != expected["years_resolved"] or state_hash(game) != expected["final_hash"] or game != final:
        raise ValueError("Replay is incomplete or does not match its final save.")
    return {"verified_years": count, "final_hash": state_hash(game), "winners": game.winners}


def aggregate(summaries):
    return {"campaigns": len(summaries), "unresolved": sum(s["stop_reason"] == "observation_limit" for s in summaries),
        "winner_counts": dict(Counter(f for s in summaries for f in s["winners"])),
        "tested_player_wins": sum(s["player"] in s["winners"] for s in summaries),
        "by_policy": {policy: {"campaigns": sum(s["policy"] == policy for s in summaries),
            "tested_player_wins": sum(s["policy"] == policy and s["player"] in s["winners"] for s in summaries),
            "unresolved": sum(s["policy"] == policy and s["stop_reason"] == "observation_limit" for s in summaries)}
            for policy in POLICIES if any(s["policy"] == policy for s in summaries)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--seeds", type=int, nargs="+", default=[17, 23])
    run.add_argument("--factions", choices=FACTIONS, nargs="+", default=list(FACTIONS))
    run.add_argument("--policies", choices=list(POLICIES), nargs="+", default=list(POLICIES))
    run.add_argument("--turns", type=int, default=30)
    commands.add_parser("replay").add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "replay":
            print(json.dumps(replay_campaign(args.directory), indent=2))
            return
        if not 1 <= args.turns <= 250 or any(not 0 <= seed <= 100000 for seed in args.seeds):
            parser.error("Use 1–250 years and seeds between 0 and 100000.")
        args.output.mkdir(parents=True, exist_ok=False)
        summaries = []
        for faction in dict.fromkeys(args.factions):
            for policy in dict.fromkeys(args.policies):
                for seed in dict.fromkeys(args.seeds):
                    name = f"{faction}-{policy}-{seed}"
                    summary, _ = run_campaign(faction, policy, seed, args.turns, directory=args.output / name)
                    replay_campaign(args.output / name)
                    summaries.append({"case": name, **summary})
                    print(f"{name}: {summary['years_resolved']} years, {summary['stop_reason']}, winners {summary['winners']}", flush=True)
        report = {"format_version": 1, "policy_fingerprint": policy_fingerprint(), "rules_version": RULES_VERSION,
            "policies": POLICIES, "observation_limit_is_game_rule": False, "human_player_observations": 0,
            "replayed_every_case": True, "aggregate": aggregate(summaries), "campaigns": summaries}
        (args.output / "results.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        print(json.dumps(report["aggregate"], indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Evaluation failed: {exc}\n")


if __name__ == "__main__":
    main()
