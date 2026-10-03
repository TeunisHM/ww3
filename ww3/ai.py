"""Computer opponents with reproducible variation and faction objectives."""

from copy import deepcopy
from random import Random

from .catalog import FACTIONS, FRONTS, GOVERNMENTS
from .engine import InvalidOrder, fresh_order, investment_cost, preview_plan
from .models import Game, pair

FRONT_WEIGHTS = {"EU": (.65, 0, .35, 0), "US": (.10, .25, .45, .20), "China": (0, .55, .45, 0), "Russia": (.60, 0, .40, 0)}


def prepare_ai_orders(game: Game) -> Game:
    """Fill other factions' orders while preserving the player's draft."""
    bots = [f for f in FACTIONS if f != game.player] if game.mode == "solo" else []
    return prepare_computer_orders(game, bots)


def prepare_computer_orders(game: Game, factions) -> Game:
    """Use the existing policy for an explicit set of factions in evaluations.

Canonical faction order keeps treaty and construction planning reproducible.
The regular client still calls prepare_ai_orders with exactly its solo rivals.
"""
    selected = set(factions)
    if not selected <= set(FACTIONS):
        raise ValueError("Unknown computer faction.")
    work = deepcopy(game)
    bots = [f for f in FACTIONS if f in selected]
    # Set all diplomacy before planning construction, so treaty discounts agree.
    for f in bots:
        n = work.nations[f]
        o = fresh_order(work, f, work.orders[f])
        debt_ratio = work.debt(f) / max(.01, n.gdp)
        o.tax_rate = min(.5, max(.22, n.tax_rate + (.025 if n.currency < 1 and debt_ratio > 1 else 0)))
        if n.content < 40:
            o.tax_rate = max(.15, o.tax_rate - .04)
        o.trade_offers = [other for other in FACTIONS if other != f and n.relations[other] >= 2.6 and n.tariffs[other] < .5]
        o.alliance_offers = [other for other in FACTIONS if other != f and n.relations[other] >= 3.7]
        o.share_bonus = [other for other in o.trade_offers if n.relations[other] >= 3.0]
        o.tariffs = {other: (.25 if n.relations[other] < 2.2 else .1 if n.relations[other] < 3 else 0.0) for other in FACTIONS if other != f}
        if n.currency > 2 and n.content > 40:
            preferred = max((p for p in FACTIONS if p != f), key=lambda p: n.relations[p])
            if n.relations[preferred] < 4.7:
                o.improve_relations = [preferred]
        if f == "US" and work.round == 2 and not n.transition_target:
            o.government = GOVERNMENTS[3]
        for c in work.contracts:
            if c.lender == f and work.round >= c.matures_round:
                o.contract_rates[c.id] = .03 if n.relations[c.borrower] >= 3.5 else .06 if n.relations[c.borrower] < 2.5 else .04
        work.orders[f] = o
    for f in bots:
        n, o = work.nations[f], work.orders[f]
        military = n.military
        rng = Random(work.rules.ai_seed + work.round * 101 + FACTIONS.index(f))
        weights = [weight * rng.uniform(.9, 1.1) for weight in FRONT_WEIGHTS[f]]
        budget = int(military * .8)
        o.deployments = {front: float(int(budget * weight / sum(weights))) for front, weight in zip(FRONTS, weights)}
        primary = FRONTS[max(range(4), key=lambda i: weights[i])]
        o.deployments[primary] += budget - sum(o.deployments.values())
        # The AI uses the same affordability preview as the player. Stop spending
        # before treasury reserves are exhausted; projects are genuine choices.
        for _ in range(40):
            left = n.productivity - sum(o.investments.values())
            if left < 1:
                break
            production = n.last_production
            priorities = []
            if production.get("energy_supply", 1) < .98 or n.energy < 12:
                priorities += ["renewable", "thermal"]
            if production.get("compute_supply", 1) < .98 or n.compute < 5:
                priorities += ["datacenter"]
            if n.content < 55:
                priorities += ["civil_investment"]
            if n.minerals < 12:
                priorities += ["mine"]
            cycle = ["factory", "research", "renewable", "infrastructure", "drone", "mine", "datacenter", "civil_investment"]
            offset = (work.round + FACTIONS.index(f)) % len(cycle)
            priorities += cycle[offset:] + cycle[:offset]
            selected = False
            for key in dict.fromkeys(priorities):
                cost = investment_cost(work, f, key)
                allocation = min(left, cost["productivity"])
                previous = o.investments.get(key, 0.0)
                o.investments[key] = previous + allocation
                try:
                    preview = preview_plan(work, f)
                    if preview["currency"] < min(.5, n.gdp * .03):
                        raise InvalidOrder("Preserve reserves")
                except InvalidOrder:
                    if previous:
                        o.investments[key] = previous
                    else:
                        del o.investments[key]
                else:
                    selected = True
                    break
            if not selected:
                break
    return work
