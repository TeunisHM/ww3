"""Deterministic, public-information policies for objective campaign playtests.

These are experimental players, not replacement opponents. They build a
supported industrial/military base and use the same one-year forecast available
to a human to choose allocations across *all* relevant objective theaters.
"""

from copy import copy, deepcopy

from .ai import prepare_ai_orders
from .catalog import FACTIONS, FRONTS
from .engine import InvalidOrder, fresh_order, investment_cost, preview_plan, resolve_round
from .strategy import objective_progress


def _compact(game):
    candidate = copy(game)
    candidate.history, candidate.reports = [], []
    return deepcopy(candidate)


def _diplomacy(game):
    f, n = game.player, game.nations[game.player]
    order = fresh_order(game, f)
    peers = [other for other in FACTIONS if other != f]
    order.tax_rate = .55 if f == "Russia" else .4
    order.trade_offers = peers
    order.tariffs = dict.fromkeys(peers, 0.0)
    # EU security explicitly rewards an American coalition. Other objectives
    # demand national shares, so permanent military blocs impede clearance.
    order.alliance_offers = ["US"] if f == "EU" else []
    order.share_bonus = []
    if n.currency > 2:
        targets = [p for p in peers if n.relations[p] < 3.75]
        # Secure Chinese productivity and American compute access first.
        priorities = [p for p in ("China", "US", "EU", "Russia") if p in targets]
        if priorities:
            order.improve_relations = priorities[:1]
    game.orders[f] = order


def _build(game, industrial):
    f, n = game.player, game.nations[game.player]
    order = game.orders[f]
    # Small economies cannot carry unlimited factory upkeep. The two variants
    # make an explicit early production-versus-immediate-arms tradeoff.
    factory_target = (6 if industrial else 3) if f == "Russia" else (12 if industrial else 6)
    reserve = min(2.0, max(.35, n.gdp * .04))
    for _ in range(60):
        left = n.productivity - sum(order.investments.values())
        if left < 1e-7:
            break
        planned = {k: n.buildings[k] + n.progress.get(k, 0) + order.investments.get(k, 0) / investment_cost(game, f, k)["productivity"]
            for k in n.buildings}
        energy_income = (planned["renewable"] * (5 + n.innovation * .1) + planned["thermal"] * 5) * (1.2 if f == "Russia" else 1)
        energy_use = planned["drone"] * 3 + planned["research"] + planned["datacenter"]
        compute_use = (planned["research"] + planned["cyber"]) * 5
        repairs = []
        if n.energy + 2 * (energy_income - energy_use) < 6:
            repairs += ["thermal", "renewable"]
        if planned["datacenter"] * 10 < compute_use:
            repairs += ["datacenter"]
        if n.minerals < 4:
            repairs += ["mine"]
        expansion = ["factory"] if planned["factory"] < factory_target else []
        income = ["infrastructure"] if f == "Russia" and n.gdp < 5 and order.investments.get("infrastructure", 0) < 20 else []
        choices = list(dict.fromkeys(repairs + expansion + income + ["drone", "cyber", "thermal", "research", "civil_investment"]))
        for key in choices:
            cost = investment_cost(game, f, key)
            previous = order.investments.get(key, 0.0)
            # Finish existing paid work before starting another project.
            paid = n.progress.get(key, 0) if not previous else 0
            amount = min(left, cost["productivity"] * (1 - paid))
            order.investments[key] = previous + amount
            try:
                preview = preview_plan(game, f)
                if preview["currency"] < reserve:
                    raise InvalidOrder("Preserve operating reserves")
            except InvalidOrder:
                if previous:
                    order.investments[key] = previous
                else:
                    del order.investments[key]
            else:
                break
        else:
            break


def _progress(game, faction):
    values = []
    for row in objective_progress(game, faction):
        current, target = row["value"], row["target"]
        if row["comparison"] in (">", ">="):
            value = current / target
        elif row["unit"] == "influence":
            value = (100 - current) / (100 - target)
        elif target == 0:
            value = 1 / (1 + current / 20)
        else:
            value = target / max(target, current)
        values.append(max(0, min(1, value)))
    return values


def _allocations(game):
    f, n = game.player, game.nations[game.player]
    first, second = (FRONTS[0], FRONTS[2]) if f in ("EU", "Russia") else (FRONTS[1], FRONTS[2])
    candidates = [dict.fromkeys(FRONTS, 0.0)]
    # A fixed, explicit search grid, with no random choices. Vary mobilization
    # as well as split: reserves avoid upkeep and allow recovery during buildup.
    for fraction in (.05, .1, .25, .5, .75, 1.0):
        budget = n.military * fraction
        for step in range(11):
            deployment = dict.fromkeys(FRONTS, 0.0)
            deployment[first], deployment[second] = budget * step / 10, budget * (10 - step) / 10
            candidates.append(deployment)
    # Find affordable precision allocations too: mobilizing 25% of a large
    # reserve can cost far more than the actual objective requires. Conditions
    # on each front are independent during combat, so bisect their forecast.
    required = dict.fromkeys(FRONTS, 0.0)
    saved = game.orders[f].deployments
    for front in (first, second):
        def sufficient(amount):
            game.orders[f].deployments = dict.fromkeys(FRONTS, 0.0)
            game.orders[f].deployments[front] = amount
            future = resolve_round(game)
            conditions = [row for row in objective_progress(future, f) if row["front"] == front and row["unit"] != "influence"]
            # A security majority alone cannot displace Russian influence;
            # Europe also needs successive uncontested years.
            cleared = not (f == "EU" and front == FRONTS[0]) or future.nations["Russia"].deployments[front] < 1e-8
            return cleared and all(row["met"] for row in conditions)

        low, high = 0.0, n.military
        if sufficient(0):
            required[front] = 0
        elif sufficient(high):
            for _ in range(17):
                midpoint = (low + high) / 2
                if sufficient(midpoint):
                    high = midpoint
                else:
                    low = midpoint
            required[front] = high
        else:
            required[front] = n.military
    game.orders[f].deployments = saved
    total = sum(required.values())
    if total:
        for fraction in (.5, .75, 1.0):
            scale = min(1, n.military / total) * fraction
            candidates.append({front: amount * scale for front, amount in required.items()})
    # US denial normally needs no South American commitment against current
    # opponents, but explicitly consider a clearing force if any appears.
    if f == "US" and any(game.orders[p].deployments[FRONTS[3]] > 0 for p in FACTIONS if p != f):
        for share in (.1, .25, .5):
            for old in list(candidates):
                deployment = {front: value * (1 - share) for front, value in old.items()}
                deployment[FRONTS[3]] = n.military * share
                candidates.append(deployment)
    return candidates


def _choose_deployments(game):
    f = game.player
    original = game.nations[f]
    best = None
    relevant = {FRONTS[0], FRONTS[2]} if f in ("EU", "Russia") else {FRONTS[1], FRONTS[2], FRONTS[3]}
    for deployment in _allocations(game):
        game.orders[f].deployments = deployment
        predicted = resolve_round(game)
        n = predicted.nations[f]
        conditions = objective_progress(predicted, f)
        progress = _progress(predicted, f)
        # Reward complete/held objective sets most, while partial progress and
        # losses inflicted on competing forces guide a multi-year campaign.
        objective = 80 * sum(row["met"] for row in conditions) + 30 * sum(progress)
        objective += 600 * predicted.objective_streaks[f]
        hostile_losses = 0
        for front in relevant:
            for other in FACTIONS:
                if other != f and not (f == "EU" and other == "US"):
                    hostile_losses += game.orders[other].deployments[front] - predicted.nations[other].deployments[front]
        own_losses = original.military + n.last_production["military"] + n.last_production["reserve_recovery"] - n.military
        score = objective + .2 * hostile_losses - .25 * own_losses
        score -= sum(deployment.values()) * game.rules.military_upkeep * (1.5 if f == "Russia" else .6)
        score -= 30 * n.last_ledger["new_borrowing"]
        score -= 1000 * max(predicted.objective_streaks[other] for other in FACTIONS if other != f)
        if f == "Russia" and not all(row["met"] for row in conditions):
            # A small economy must build an invasion reserve instead of paying
            # to hold a partial front indefinitely while its treasury collapses.
            score -= 15 * max(0, 1 - original.currency / 10) * max(0, -n.last_ledger["operating_balance"])
        # Stable tie-breaking prefers fewer mobilized forces, then grid order.
        terminal = 1 if f in predicted.winners else -1 if predicted.winners else 0
        key = (terminal, round(score, 9), -sum(deployment.values()))
        if best is None or key > best[0]:
            best = key, dict(deployment)
    game.orders[f].deployments = best[1]


def prepare_objective_orders(game, *, industrial=False):
    """Return valid real orders without changing the supplied game or RNG."""
    work = _compact(game)
    _diplomacy(work)
    work = prepare_ai_orders(work)
    _build(work, industrial)
    _choose_deployments(work)
    # Restore the actual campaign chronicle after the disposable search copies.
    work.history, work.reports = deepcopy(game.history), deepcopy(game.reports)
    return work
