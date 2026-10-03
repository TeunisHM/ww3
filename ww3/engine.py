"""Pure, deterministic simulation. Resolving orders never mutates its input.

A planning phase uses the resources currently shown. End-year commits all
orders, then the system produces resources, updates relations, and resolves
military activity for the next planning phase, in the source document's order.
"""

from copy import copy, deepcopy
from itertools import combinations
import math

from .catalog import FACTIONS, FRONTS, GOVERNMENTS, SCENARIO
from .models import Contract, Front, Game, Nation, Order, pair
from .rules import BUILDINGS, GOVERNMENT_EFFECTS, INVESTMENTS, PROJECTS, Rules
from .strategy import coalitions, dominance_bonus, update_victory
from .reporting import TurnReport

EPS = 1e-8


class InvalidOrder(ValueError):
    pass


def clamp(value, low, high):
    return max(low, min(high, value))


def number(value, low=0, high=1e12):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and low <= value <= high


def has_bonus(game: Game, receiver: str, provider: str) -> bool:
    if receiver == provider:
        return True
    return pair(receiver, provider) in game.trades and (provider == "EU" or receiver in game.nations[provider].share_bonus)


def compute_multiplier(game: Game, faction: str) -> float:
    return .8 if has_bonus(game, faction, "US") else 1.0


def innovation_multiplier(n: Nation) -> float:
    return (1.1 if n.id in ("EU", "China") else 1.0) * GOVERNMENT_EFFECTS[n.government]["innovation"]


def productivity_capacity(game: Game, faction: str) -> float:
    n = game.nations[faction]
    initial_modifier = (1.2 if faction == "China" else 1) * GOVERNMENT_EFFECTS[SCENARIO[faction]["government"]]["productivity"]
    legacy_base = game.rules.starting_productivity[faction] / initial_modifier
    added_factories = n.buildings["factory"] - game.rules.starting_buildings[faction]["factory"]
    return (legacy_base + added_factories * game.rules.factory_output) * (1.2 if has_bonus(game, faction, "China") else 1) * GOVERNMENT_EFFECTS[n.government]["productivity"]


def domestic_interest(game: Game, faction: str) -> float:
    return game.rules.domestic_base_interest + (100 - game.nations[faction].content) / 100 * game.rules.domestic_discontent_interest


def investment_cost(game: Game, faction: str, key: str) -> dict[str, float]:
    spec = INVESTMENTS[key]
    discount = .75 if key == "datacenter" and has_bonus(game, faction, "EU") else 1.0
    # Innovation affects material/currency costs, not the stated 10-point work cost.
    efficiency = max(.7, 1 - game.nations[faction].innovation * .001)
    return {
        "currency": spec.currency * discount * efficiency,
        "minerals": spec.minerals * discount * efficiency,
        "energy": spec.energy_upkeep if key in PROJECTS else 0.0,
        "compute": spec.compute_upkeep * compute_multiplier(game, faction) if key in PROJECTS else 0.0,
        "productivity": spec.productivity * discount,
    }


def fresh_order(game: Game, faction: str, previous: Order | None = None) -> Order:
    n = game.nations[faction]
    return Order(
        tax_rate=n.tax_rate, government=n.transition_target or n.government,
        deployments=dict(n.deployments), tariffs=dict(n.tariffs),
        trade_offers=list(previous.trade_offers) if previous else [f for f in FACTIONS if f != faction and pair(f, faction) in game.trades],
        alliance_offers=list(previous.alliance_offers) if previous else [f for f in FACTIONS if f != faction and pair(f, faction) in game.alliances],
        share_bonus=list(n.share_bonus),
    )


def snapshot(game: Game) -> dict:
    return {"year": game.year, "round": game.round, "nations": {
        f: {"gdp": n.gdp, "currency": n.currency, "debt": game.debt(f), "content": n.content,
            "innovation": n.innovation, "military": n.military, "influence": game.influence(f),
            "energy": n.energy, "minerals": n.minerals}
        for f, n in game.nations.items()}}


def new_game(mode="solo", player="EU", rules: Rules | None = None) -> Game:
    if mode not in ("solo", "hotseat", "sandbox") or player not in FACTIONS:
        raise ValueError("Choose a valid game mode and faction.")
    rules = deepcopy(rules or Rules())
    nations = {}
    for f, source in SCENARIO.items():
        nations[f] = Nation(
            id=f, government=source["government"], currency=rules.starting_capital[f],
            gdp=source["gdp"], tax_rate=source["tax_rate"],
            domestic_debt=source["debt"] * source["domestic_share"], military=source["military"],
            military_capacity=source["military"],
            buildings=dict(rules.starting_buildings[f]), relations=dict(source["relations"]),
            tariffs={other: 0.0 for other in FACTIONS if other != f},
            energy=rules.starting_energy[f], minerals=rules.starting_minerals[f],
            innovation=rules.starting_innovation[f], content=rules.starting_content[f],
            deployments=dict(rules.starting_deployments[f]),
        )
    contracts = []
    for borrower, source in SCENARIO.items():
        external = source["debt"] * (1 - source["domestic_share"])
        total_weight = sum(SCENARIO[lender]["creditor_weight"] for lender in FACTIONS if lender != borrower)
        for lender in FACTIONS:
            if lender != borrower:
                contracts.append(Contract(f"{borrower}:{lender}", borrower, lender,
                    external * SCENARIO[lender]["creditor_weight"] / total_weight,
                    rules.foreign_interest, rules.contract_years))
    game = Game(nations, contracts, {name: Front(name, dict(rules.starting_influence[name])) for name in FRONTS}, {}, rules, mode=mode, player=player)
    for f, n in nations.items():
        n.productivity = productivity_capacity(game, f)
        n.compute = 0.0
        game.orders[f] = fresh_order(game, f)
    for name, front in game.fronts.items():
        groups = coalitions(game, name)
        front.status = "Contested" if len(groups) > 1 else " + ".join(groups[0]) + " · uncontested" if groups else "Uncommitted"
    game.history.append(snapshot(game))
    return game


def validate_order(game: Game, faction: str, order: Order) -> list[str]:
    n = game.nations[faction]
    errors = []
    peers = set(FACTIONS) - {faction}
    if not number(order.tax_rate, 0, .75):
        errors.append("Tax rate must be between 0% and 75%.")
    if order.government not in GOVERNMENTS:
        errors.append("Unknown government type.")
    if n.transition_target and order.government != n.transition_target:
        errors.append("A government transition is already in progress.")
    if set(order.deployments) != set(FRONTS) or not all(number(v) for v in order.deployments.values()):
        errors.append("Every front needs a nonnegative, finite deployment.")
    elif sum(order.deployments.values()) > n.military + EPS:
        errors.append(f"Deployments exceed available military power ({n.military:.1f}).")
    if not set(order.investments) <= set(INVESTMENTS) or not all(number(v, 0, 10000) for v in order.investments.values()):
        errors.append("Unknown investment or invalid productivity allocation.")
    elif sum(order.investments.values()) > n.productivity + EPS:
        errors.append(f"Investment allocations exceed this year's productivity ({n.productivity:.1f}).")
    if not set(order.tariffs) <= peers or not all(number(v, 0, .5) for v in order.tariffs.values()):
        errors.append("Tariffs must name a foreign faction and be between 0% and 50%.")
    for values in (order.trade_offers, order.alliance_offers, order.share_bonus, order.improve_relations, order.foreign_aid):
        if not isinstance(values, list) or not all(isinstance(v, str) and v in peers for v in values) or len(set(values)) != len(values):
            errors.append("Diplomatic actions must name each foreign faction at most once.")
    if not number(order.domestic_repayment, 0, n.domestic_debt + EPS):
        errors.append("Domestic repayment must be between zero and outstanding domestic debt.")
    contracts = {c.id: c for c in game.contracts}
    for cid, rate in order.contract_rates.items():
        c = contracts.get(cid)
        if not c or c.lender != faction or game.round < c.matures_round or not number(rate, 0, .2):
            errors.append("Only the lender may change a matured contract's rate (0–20%).")
    for cid, amount in order.foreign_repayments.items():
        c = contracts.get(cid)
        if not c or c.borrower != faction or game.round < c.matures_round or not number(amount, 0, c.principal + EPS):
            errors.append("Foreign principal can only be repaid by its borrower at maturity.")
    return errors


def _spend(n: Nation, cost: dict, label: str):
    for resource in ("currency", "minerals", "energy", "compute"):
        if getattr(n, resource) + EPS < cost.get(resource, 0):
            raise InvalidOrder(f"{n.id}: {label} needs {cost[resource]:.2f} {resource}; only {getattr(n, resource):.2f} remains in this plan.")
    for resource in ("currency", "minerals", "energy", "compute"):
        setattr(n, resource, max(0, getattr(n, resource) - cost.get(resource, 0)))


def _invest(game: Game, f: str, messages: list[str]):
    n = game.nations[f]
    for key in INVESTMENTS:
        allocation = game.orders[f].investments.get(key, 0.0)
        remaining = allocation
        spec = INVESTMENTS[key]
        cost = investment_cost(game, f, key)
        # Store work as a fraction, so a later discount cannot invalidate paid work.
        while remaining > EPS:
            progress = n.progress.get(key, 0.0)
            if progress <= EPS:
                _spend(n, cost, spec.name)
            work = min(remaining, (1 - progress) * cost["productivity"])
            progress += work / cost["productivity"]
            remaining -= work
            if progress >= 1 - EPS:
                n.progress.pop(key, None)
                if key in BUILDINGS:
                    n.buildings[key] += 1
                    if key == "datacenter":
                        n.innovation += innovation_multiplier(n)
                elif key == "research_grant":
                    n.innovation += 2 * (.5 + n.content / 100) * innovation_multiplier(n)
                elif key == "civil_investment":
                    n.civic_support += 3
                    n.content = min(100, n.content + 3)
                elif key == "infrastructure":
                    n.gdp += .25
                elif key == "modernization":
                    gain = 10 * (1 + n.innovation / 100)
                    n.military += gain
                    n.military_capacity += gain
                messages.append(f"{f} completed {spec.name.lower()}.")
            else:
                n.progress[key] = progress
                break


def _prepare(game: Game) -> tuple[Game, list[str], dict]:
    for f in FACTIONS:
        errors = validate_order(game, f, game.orders[f])
        if errors:
            raise InvalidOrder(f"{f}: " + " ".join(errors))
    work = deepcopy(game)
    messages = []
    cash_before = {f: n.currency for f, n in work.nations.items()}
    # Mutual offers are resolved simultaneously; either party may withdraw.
    for attr, field, label in (("trades", "trade_offers", "trade agreement"), ("alliances", "alliance_offers", "military alliance")):
        pacts = []
        for a, b in combinations(FACTIONS, 2):
            p = pair(a, b)
            accepted = b in getattr(work.orders[a], field) and a in getattr(work.orders[b], field)
            if accepted:
                pacts.append(p)
                if p not in getattr(game, attr):
                    messages.append(f"{a} and {b} signed a {label}.")
            elif p in getattr(game, attr):
                messages.append(f"{a} and {b} ended their {label}.")
        setattr(work, attr, pacts)
    for f in FACTIONS:
        n = work.nations[f]
        order = work.orders[f]
        n.tax_rate = order.tax_rate
        n.tariffs = {other: order.tariffs.get(other, 0.0) for other in FACTIONS if other != f}
        n.share_bonus = list(order.share_bonus)
        n.deployments = dict(order.deployments)
        if order.government != n.government and not n.transition_target:
            n.transition_target = order.government
            n.transition_remaining = work.rules.government_transition_years
            messages.append(f"{f} began a {n.transition_remaining}-year transition to {n.transition_target}.")
    # Discretionary spending must be affordable from existing reserves. Incoming
    # principal/interest cannot fund same-phase orders: no iteration-order advantage.
    repayments = []
    aid_transfers = []
    for f in FACTIONS:
        n = work.nations[f]
        order = work.orders[f]
        _spend(n, {"currency": len(order.improve_relations) * work.rules.diplomacy_cost}, "diplomatic outreach")
        for recipient in order.foreign_aid:
            _spend(n, {"currency": work.rules.foreign_aid_amount}, "foreign aid")
            aid_transfers.append((f, recipient, work.rules.foreign_aid_amount))
        _spend(n, {"currency": order.domestic_repayment}, "domestic debt repayment")
        n.domestic_debt = max(0, n.domestic_debt - order.domestic_repayment)
        for cid, amount in order.foreign_repayments.items():
            _spend(n, {"currency": amount}, "foreign debt repayment")
            repayments.append((cid, amount))
        _invest(work, f, messages)
    spending = {f: cash_before[f] - n.currency for f, n in work.nations.items()}
    principal_received = dict.fromkeys(FACTIONS, 0.0)
    aid_received = dict.fromkeys(FACTIONS, 0.0)
    for donor, recipient, amount in aid_transfers:
        work.nations[recipient].currency += amount
        aid_received[recipient] += amount
        messages.append(f"{donor} sent {amount:.2f} T in foreign aid to {recipient}.")
    for cid, amount in repayments:
        c = next(c for c in work.contracts if c.id == cid)
        c.principal = max(0, c.principal - amount)
        work.nations[c.lender].currency += amount
        principal_received[c.lender] += amount
        if amount > EPS:
            messages.append(f"{c.borrower} repaid {amount:.3f} T of debt to {c.lender}.")
    for c in work.contracts:
        if work.round >= c.matures_round:
            old = c.rate
            c.rate = work.orders[c.lender].contract_rates.get(c.id, c.rate)
            c.matures_round = work.round + work.rules.contract_years
            if c.principal > EPS:
                delta = -(c.rate - old) * 5
                _relation(work, c.borrower, c.lender, delta)
                messages.append(f"{c.borrower} → {c.lender}: debt contract renewed at {c.rate:.1%} for {work.rules.contract_years} years.")
    return work, messages, {f: {"opening_currency": cash_before[f], "planned_spending": -spending[f], "principal_received": principal_received[f], "aid_received": aid_received[f]} for f in FACTIONS}


def plan_errors(game: Game) -> list[str]:
    try:
        _prepare(game)
        return []
    except InvalidOrder as exc:
        return [str(exc)]


def preview_plan(game: Game, faction: str) -> dict:
    """Preview one plan without advancing time or exposing errors in other plans."""
    # Historical reports do not affect orders. AI affordability probes can run
    # many times per draft; avoid copying the entire chronicle for each probe.
    candidate = copy(game)
    candidate.history, candidate.reports = [], []
    candidate = deepcopy(candidate)
    for f in FACTIONS:
        if f != faction:
            previous = candidate.orders[f]
            candidate.orders[f] = fresh_order(candidate, f, previous)
            candidate.orders[f].share_bonus = list(previous.share_bonus)
    work, messages, ledger = _prepare(candidate)
    n = work.nations[faction]
    return {"currency": n.currency, "energy": n.energy, "minerals": n.minerals, "compute": n.compute,
            "spending": -ledger[faction]["planned_spending"], "messages": [m for m in messages if m.startswith(faction + " ")]}


def _relation(game: Game, a: str, b: str, delta: float):
    value = clamp(game.nations[a].relations[b] + delta, 1.0, 5.0)
    game.nations[a].relations[b] = value
    game.nations[b].relations[a] = value


def _produce(game: Game, f: str, messages: list[str]):
    n = game.nations[f]
    b = n.buildings
    resource_bonus = 1.2 if f == "Russia" else 1
    mineral_output = b["mine"] * 5 * resource_bonus
    n.minerals += mineral_output
    thermal_demand = b["thermal"] * .1
    thermal_ratio = min(1, n.minerals / thermal_demand) if thermal_demand else 1
    n.minerals -= thermal_demand * thermal_ratio
    energy_output = (b["renewable"] * (5 + .1 * n.innovation) + b["thermal"] * 5 * thermal_ratio) * resource_bonus
    n.energy += energy_output
    energy_demand = sum(b[k] * spec.energy_upkeep for k, spec in BUILDINGS.items())
    energy_ratio = min(1, n.energy / energy_demand) if energy_demand else 1
    n.energy = max(0, n.energy - energy_demand * energy_ratio)
    # Energy shortages proportionally reduce all energy-dependent facilities.
    compute_output = b["datacenter"] * 10 * energy_ratio
    compute_demand = (b["cyber"] * 5 + b["research"] * 5 * energy_ratio) * compute_multiplier(game, f)
    compute_ratio = min(1, compute_output / compute_demand) if compute_demand else 1
    n.compute = max(0, compute_output - compute_demand * compute_ratio)
    n.productivity = productivity_capacity(game, f)
    innovation_gain = b["research"] * energy_ratio * compute_ratio * (.5 + n.content / 100) * innovation_multiplier(n)
    military_gain = b["drone"] * 10 * (1 + n.innovation / 100) * energy_ratio + b["cyber"] * (5 + .1 * n.innovation) * compute_ratio
    n.innovation += innovation_gain
    n.military += military_gain
    n.military_capacity += military_gain
    reserve = n.military - sum(n.deployments.values())
    recovered = min(max(0, n.military_capacity - n.military), n.military_capacity * game.rules.reserve_recovery) if reserve > EPS else 0.0
    n.military += recovered
    n.last_production = {"energy": energy_output, "energy_used": energy_demand * energy_ratio,
        "minerals": mineral_output, "minerals_used": thermal_demand * thermal_ratio,
        "compute": compute_output, "compute_used": compute_demand * compute_ratio,
        "productivity": n.productivity, "innovation": innovation_gain, "military": military_gain, "reserve_recovery": recovered,
        "energy_supply": energy_ratio, "compute_supply": compute_ratio, "thermal_supply": thermal_ratio}
    if min(energy_ratio, compute_ratio, thermal_ratio) < 1 - EPS:
        messages.append(f"{f}: shortages reduced production (energy {energy_ratio:.0%}, compute {compute_ratio:.0%}, thermal fuel {thermal_ratio:.0%}).")


def _economy(game: Game, opening_ledgers: dict, messages: list[str]):
    # GDP, military upkeep and interest are sampled together, before any transfers.
    gdp = {f: n.gdp for f, n in game.nations.items()}
    military = {f: sum(n.deployments.values()) for f, n in game.nations.items()}
    interest_paid = {f: sum(c.principal * c.rate for c in game.contracts if c.borrower == f) for f in FACTIONS}
    interest_received = {f: sum(c.principal * c.rate for c in game.contracts if c.lender == f) for f in FACTIONS}
    for f in FACTIONS:
        n = game.nations[f]
        _produce(game, f, messages)
        trade = tariffs = luxury = 0.0
        for other in FACTIONS:
            if other == f:
                continue
            a, b = n.tariffs[other], game.nations[other].tariffs[f]
            openness = (1 - a) * (1 - b)
            agreement = pair(f, other) in game.trades
            if agreement:
                trade += min(gdp[f], gdp[other]) * game.rules.trade_volume * openness
            tariffs += gdp[other] * game.rules.trade_volume * a * openness * (1 if agreement else .25)
            if f == "EU":
                luxury += gdp[other] * game.rules.luxury_export_rate
        ledger = dict(opening_ledgers[f])
        ledger.update({"taxes": gdp[f] * n.tax_rate, "trade_income": trade, "tariff_income": tariffs,
            "dominance_income": gdp[f] * n.tax_rate * dominance_bonus(game, f),
            "luxury_exports": luxury, "interest_received": interest_received[f],
            "domestic_interest": -n.domestic_debt * domestic_interest(game, f),
            "foreign_interest": -interest_paid[f],
            "building_upkeep": -sum(n.buildings[k] * spec.currency_upkeep for k, spec in BUILDINGS.items()),
            "military_upkeep": -military[f] * game.rules.military_upkeep})
        operating = sum(value for key, value in ledger.items() if key not in ("opening_currency", "planned_spending", "principal_received", "aid_received"))
        n.currency += operating
        borrowing = max(0, -n.currency)
        if borrowing > EPS:
            n.domestic_debt += borrowing
            n.currency = 0.0
            messages.append(f"{f} issued {borrowing:.3f} T in domestic debt to cover its budget shortfall.")
        ledger["new_borrowing"] = borrowing
        ledger["operating_balance"] = operating
        ledger["closing_currency"] = n.currency
        n.last_ledger = ledger


def _diplomacy(game: Game):
    for a, b in combinations(FACTIONS, 2):
        delta = -game.rules.hostility_drift
        if pair(a, b) in game.trades:
            delta += game.rules.trade_relation_gain
        delta -= (game.nations[a].tariffs[b] + game.nations[b].tariffs[a]) * game.rules.tariff_relation_penalty
        for actor, target in ((a, b), (b, a)):
            if target in game.orders[actor].improve_relations:
                delta += game.rules.diplomacy_gain * (1.1 if actor == "US" else 1)
            if target in game.orders[actor].foreign_aid:
                delta += game.rules.foreign_aid_relation_gain * (1.1 if actor == "US" else 1)
        _relation(game, a, b, delta)


def _gain_influence(front: Front, winners: list[str], deployments: dict[str, float], gain: float):
    # A front contains at most 100 influence. Rivals' established influence is
    # displaced proportionally when there is no unclaimed influence left.
    gain = min(gain, 100 - sum(front.influence[f] for f in winners))
    available = max(0, 100 - sum(front.influence.values()))
    displaced = max(0, gain - available)
    rivals = [f for f in FACTIONS if f not in winners]
    rival_total = sum(front.influence[f] for f in rivals)
    if rival_total > EPS:
        for f in rivals:
            front.influence[f] = max(0, front.influence[f] - displaced * front.influence[f] / rival_total)
    strength = sum(deployments[f] for f in winners)
    if strength > EPS:
        for f in winners:
            front.influence[f] += gain * deployments[f] / strength


def _military(game: Game, messages: list[str]) -> dict[str, int]:
    involved = dict.fromkeys(FACTIONS, 0)
    for n in game.nations.values():
        n.last_production["mobilized"] = sum(n.deployments.values())
    for name, front in game.fronts.items():
        groups = coalitions(game, name)
        deployed = {f: game.nations[f].deployments[name] for f in FACTIONS}
        if not groups:
            front.status = "Uncommitted"
            continue
        if len(groups) == 1:
            _gain_influence(front, groups[0], deployed, game.rules.influence_gain)
            front.status = " + ".join(groups[0]) + " · uncontested"
            messages.append(f"{name}: {' + '.join(groups[0])} gained influence without opposition.")
            continue
        losses = dict.fromkeys(FACTIONS, 0.0)
        group_strength = [sum(deployed[f] for f in group) for group in groups]
        for idx, group in enumerate(groups):
            enemy = max(group_strength[j] for j in range(len(groups)) if j != idx)
            # Russian experience protects its coalition, matching combined forces.
            decay = game.rules.combat_base_decay * group_strength[idx] + game.rules.combat_attrition * (enemy - group_strength[idx])
            damage = max(0, decay) * (.9 if "Russia" in group else 1)
            total_loss = min(group_strength[idx], damage)
            for f in group:
                losses[f] = total_loss * deployed[f] / group_strength[idx]
                involved[f] += 1
        for i, group in enumerate(groups):
            for opponent in groups[i + 1:]:
                for a in group:
                    for b in opponent:
                        _relation(game, a, b, -game.rules.conflict_relation_penalty)
        for f, loss in losses.items():
            game.nations[f].military = max(0, game.nations[f].military - loss)
            game.nations[f].deployments[name] = max(0, deployed[f] - loss)
        survivors = [g for g in groups if sum(game.nations[f].deployments[name] for f in g) > EPS]
        if len(survivors) == 1:
            remaining = {f: game.nations[f].deployments[name] for f in FACTIONS}
            _gain_influence(front, survivors[0], remaining, game.rules.influence_gain)
            front.status = " + ".join(survivors[0]) + " · breakthrough"
        else:
            front.status = "Contested" if survivors else "Mutual withdrawal"
        summary = ", ".join(f"{f} −{loss:.1f}" for f, loss in losses.items() if loss > EPS)
        messages.append(f"{name}: {front.status.lower()}; military losses {summary or 'none'}.")
    return involved


def _society(game: Game, wars: dict, messages: list[str]):
    for f in FACTIONS:
        n = game.nations[f]
        prod = n.last_production
        previous_content = n.content
        positive = min(10, n.innovation * .1) + n.civic_support
        negative = 50 * n.tax_rate + .003 * prod["mobilized"] + n.buildings["mine"] + wars[f] * game.rules.war_discontent
        gov_content = GOVERNMENT_EFFECTS[n.government]["content"]
        positive += max(0, gov_content)
        negative += max(0, -gov_content)
        negative += (1 - min(prod["energy_supply"], prod["compute_supply"], prod["thermal_supply"])) * 4
        if n.transition_remaining:
            negative += game.rules.transition_unrest
            n.transition_remaining -= 1
            if n.transition_remaining == 0:
                n.government = n.transition_target
                n.transition_target = None
                messages.append(f"{f} completed its government transition: {n.government}.")
        n.content = clamp(100 + positive - negative * (.9 if f == "US" else 1), 0, 100)
        growth = clamp(.01 + (previous_content - 50) * .0003 + n.innovation * .0001
            - max(0, n.tax_rate - .3) * .04 - wars[f] * .003
            - (1 - prod["energy_supply"]) * .02, -.05, .05)
        n.gdp *= 1 + growth
        n.content = clamp(n.content + max(0, growth) * 10, 0, 100)
        n.last_production["gdp_growth"] = growth
        # Update government-dependent productivity for the new planning phase.
        n.productivity = productivity_capacity(game, f)


def resolve_round(game: Game) -> Game:
    work, messages, ledgers = _prepare(game)
    report = TurnReport(game, messages)
    report.orders(work, ledgers)
    _economy(work, ledgers, messages)
    report.economy(work)
    relations = {f: dict(n.relations) for f, n in work.nations.items()}
    _diplomacy(work)
    report.relations(work, relations)
    deployed = {f: dict(n.deployments) for f, n in work.nations.items()}
    wars = _military(work, messages)
    report.combat(work, deployed)
    _society(work, wars, messages)
    report.society(work)
    update_victory(work, messages)
    report.objectives(work)
    work.reports.append({"round": game.round, "year": game.year, "messages": messages,
        "ledgers": {f: dict(n.last_ledger) for f, n in work.nations.items()}, **report.metadata()})
    work.reports = work.reports[-100:]
    work.round += 1
    work.submitted = []
    for f in FACTIONS:
        work.orders[f] = fresh_order(work, f, game.orders[f])
    work.history.append(snapshot(work))
    work.history = work.history[-250:]
    return work
