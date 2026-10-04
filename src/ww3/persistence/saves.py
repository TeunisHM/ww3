"""Portable JSON saves with a versioned, validated schema; never pickle."""

from dataclasses import asdict, fields
import json

from ww3.core.catalog import FACTIONS, FRONTS, GOVERNMENTS, SCENARIO
from ww3.core.engine import number, validate_order
from ww3.core.models import Contract, Front, Game, Nation, Order, RULES_VERSION, pair
from ww3.core.reporting import PHASES
from ww3.core.rules import BUILDINGS, GOVERNMENT_EFFECTS, INVESTMENTS, Rules

MAX_SAVE_BYTES = 2_000_000


def dumps(game: Game) -> str:
    return json.dumps(game.to_dict(), indent=2, allow_nan=False)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _record(cls, data):
    _require(isinstance(data, dict) and set(data) == {f.name for f in fields(cls)}, f"Invalid {cls.__name__} fields.")
    return cls(**data)


def _numeric_tree(value):
    if isinstance(value, dict):
        return all(isinstance(k, str) and _numeric_tree(v) for k, v in value.items())
    if isinstance(value, list):
        return all(_numeric_tree(v) for v in value)
    if isinstance(value, (float, int)) and not isinstance(value, bool):
        return number(value, -1e15, 1e15)
    return value is None or isinstance(value, (str, bool))


def _migrate_prototype(data):
    """Preserve a v1 world's assets and history while adopting the final rules."""
    old_rules = data["rules"]
    defaults = asdict(Rules())
    for name in ("starting_energy", "starting_minerals", "starting_content", "starting_innovation"):
        old_rules[name] = {f: old_rules[name] for f in FACTIONS}
    old_rules["starting_productivity"] = {
        f: old_rules["starting_buildings"][f]["factory"] * old_rules["factory_output"]
        * (1.2 if f == "China" else 1) * GOVERNMENT_EFFECTS[SCENARIO[f]["government"]]["productivity"]
        for f in FACTIONS}
    for name, value in defaults.items():
        old_rules.setdefault(name, value)
    old_rules["victory_mode"] = "influence" if old_rules["victory_target"] > 0 else "open"
    old = data.pop("winner", None)
    data["winners"] = [old] if old else []
    data["objective_streaks"] = dict.fromkeys(FACTIONS, 0)
    for f, n in data["nations"].items():
        n["military_capacity"] = max(n["military"], SCENARIO[f]["military"])
        n["civic_support"] = 0.0
        n["tariffs"] = {p: min(.5, value) for p, value in n["tariffs"].items()}
        data["orders"][f].setdefault("foreign_aid", [])
        data["orders"][f]["tariffs"] = {p: min(.5, value) for p, value in data["orders"][f]["tariffs"].items()}
    return data


def loads(payload: str | bytes, *, allow_invalid_drafts=False) -> Game:
    try:
        _require(len(payload.encode() if isinstance(payload, str) else payload) <= MAX_SAVE_BYTES, "Save file exceeds 2 MB.")
        data = json.loads(payload)
        _require(isinstance(data, dict), "Invalid save file.")
        version = data.pop("schema_version", None)
        _require(type(version) is int and version in (1, 2, 3), "Unsupported save-file version.")
        if version == 3:
            _require(data.pop("rules_version", None) == RULES_VERSION, "Unsupported gameplay rules version.")
        _require(_numeric_tree(data), "Save contains invalid or non-finite numbers.")
        if version == 1:
            data = _migrate_prototype(data)
        rules = _record(Rules, data["rules"])
        _require(set(rules.starting_capital) == set(FACTIONS) and all(number(v) for v in rules.starting_capital.values()), "Invalid starting capital.")
        _require(set(rules.starting_buildings) == set(FACTIONS), "Invalid starting buildings.")
        for building_map in rules.starting_buildings.values():
            _require(set(building_map) == set(BUILDINGS) and all(type(v) is int and 0 <= v <= 10000 for v in building_map.values()), "Invalid starting building counts.")
        for key in ("contract_years", "government_transition_years", "objective_hold_years"):
            _require(type(getattr(rules, key)) is int and 1 <= getattr(rules, key) <= 20, f"Invalid {key}.")
        _require(type(rules.start_year) is int and 1900 <= rules.start_year <= 3000, "Invalid start year.")
        for field in fields(Rules):
            value = getattr(rules, field.name)
            if not field.name.startswith("starting_") and field.name != "victory_mode":
                _require(number(value), f"Invalid rule: {field.name}.")
        for name in ("starting_energy", "starting_minerals", "starting_content", "starting_innovation", "starting_productivity"):
            values = getattr(rules, name)
            limit = 100 if name == "starting_content" else 1e12
            _require(isinstance(values, dict) and set(values) == set(FACTIONS) and all(number(v, 0, limit) for v in values.values()), f"Invalid {name}.")
        _require(set(rules.starting_deployments) == set(FACTIONS), "Invalid opening deployments.")
        for f, values in rules.starting_deployments.items():
            _require(set(values) == set(FRONTS) and all(number(v) for v in values.values()) and sum(values.values()) <= SCENARIO[f]["military"] + 1e-7, "Invalid opening deployments.")
        _require(set(rules.starting_influence) == set(FRONTS), "Invalid opening influence.")
        for values in rules.starting_influence.values():
            _require(set(values) == set(FACTIONS) and all(number(v, 0, 100) for v in values.values()) and sum(values.values()) <= 100 + 1e-7, "Invalid opening influence.")
        _require(0 <= rules.combat_attrition <= 1 and 0 <= rules.combat_base_decay <= 1 and 0 <= rules.reserve_recovery <= 1 and 0 <= rules.influence_gain <= 100, "Invalid combat settings.")
        _require(0 < rules.factory_output <= 1000 and type(rules.ai_seed) is int, "Invalid economic or AI settings.")
        _require(rules.victory_target <= 400, "Invalid influence objective.")
        _require(rules.victory_mode in ("objectives", "open", "influence") and (rules.victory_mode != "influence" or rules.victory_target > 0), "Invalid victory mode.")
        _require(set(data["nations"]) == set(FACTIONS) and set(data["orders"]) == set(FACTIONS), "Save must contain all four factions.")
        _require(set(data["fronts"]) == set(FRONTS), "Save must contain all four fronts.")
        data["rules"] = rules
        data["nations"] = {f: _record(Nation, n) for f, n in data["nations"].items()}
        data["orders"] = {f: _record(Order, o) for f, o in data["orders"].items()}
        data["fronts"] = {f: _record(Front, front) for f, front in data["fronts"].items()}
        _require(isinstance(data["contracts"], list) and len(data["contracts"]) <= 12, "Invalid debt contracts.")
        data["contracts"] = [_record(Contract, c) for c in data["contracts"]]
        game = _record(Game, data)
        _require(game.mode in ("solo", "hotseat", "sandbox") and game.player in FACTIONS, "Invalid game mode or player.")
        _require(type(game.round) is int and 1 <= game.round <= 100000, "Invalid round number.")
        _require(isinstance(game.winners, list) and len(game.winners) == len(set(game.winners)) and set(game.winners) <= set(FACTIONS), "Invalid victory state.")
        _require(set(game.objective_streaks) == set(FACTIONS) and all(type(v) is int and 0 <= v <= rules.objective_hold_years for v in game.objective_streaks.values()), "Invalid objective progress.")
        _require(isinstance(game.submitted, list) and len(set(game.submitted)) == len(game.submitted) and set(game.submitted) <= set(FACTIONS), "Invalid submitted orders.")
        pairs = {pair(a, b) for a in FACTIONS for b in FACTIONS if a != b}
        for values in (game.trades, game.alliances):
            _require(isinstance(values, list) and len(values) == len(set(values)) and set(values) <= pairs, "Invalid agreement.")
        for f, n in game.nations.items():
            peers = set(FACTIONS) - {f}
            _require(n.id == f and n.government in GOVERNMENTS, "Invalid faction or government.")
            for key in ("currency", "gdp", "domestic_debt", "military", "military_capacity", "civic_support", "innovation", "energy", "minerals", "compute", "productivity"):
                _require(number(getattr(n, key)), f"Invalid {f} {key}.")
            _require(number(n.content, 0, 100) and number(n.tax_rate, 0, .75), "Invalid content or tax rate.")
            _require(set(n.buildings) == set(BUILDINGS) and all(type(v) is int and 0 <= v <= 100000 for v in n.buildings.values()), "Invalid building count.")
            _require(set(n.deployments) == set(FRONTS) and all(number(v) for v in n.deployments.values()) and sum(n.deployments.values()) <= n.military + 1e-7, "Invalid deployed forces.")
            _require(n.military <= n.military_capacity + 1e-7, "Military strength exceeds capacity.")
            _require(set(n.relations) == peers and all(number(v, 1, 5) for v in n.relations.values()), "Invalid relationships.")
            _require(set(n.tariffs) == peers and all(number(v, 0, .5) for v in n.tariffs.values()), "Invalid tariffs.")
            _require(set(n.progress) <= set(INVESTMENTS) and all(number(v, 0, 1 - 1e-9) for v in n.progress.values()), "Invalid construction progress.")
            _require(isinstance(n.share_bonus, list) and set(n.share_bonus) <= peers, "Invalid shared bonuses.")
            _require(type(n.transition_remaining) is int and 0 <= n.transition_remaining <= rules.government_transition_years, "Invalid government transition.")
            _require((n.transition_remaining == 0 and n.transition_target is None) or (n.transition_remaining > 0 and n.transition_target in GOVERNMENTS), "Invalid government transition target.")
            for values in (n.last_ledger, n.last_production):
                _require(isinstance(values, dict) and all(number(v, -1e12, 1e12) for v in values.values()), "Invalid economic report.")
            for other in peers:
                _require(abs(n.relations[other] - game.nations[other].relations[f]) < 1e-7, "Relationships must be symmetric.")
        contract_ids = set()
        for c in game.contracts:
            _require(c.borrower in FACTIONS and c.lender in FACTIONS and c.borrower != c.lender, "Invalid contract parties.")
            _require(c.id == f"{c.borrower}:{c.lender}" and c.id not in contract_ids, "Duplicate or invalid contract ID.")
            contract_ids.add(c.id)
            _require(number(c.principal) and number(c.rate, 0, .2) and type(c.matures_round) is int and c.matures_round >= 1, "Invalid debt contract terms.")
        for name, front in game.fronts.items():
            _require(front.name == name and isinstance(front.status, str), "Invalid front.")
            _require(set(front.influence) == set(FACTIONS) and all(number(v, 0, 100 + 1e-7) for v in front.influence.values()) and sum(front.influence.values()) <= 100 + 1e-7, "Invalid influence.")
        for f, order in game.orders.items():
            for key in ("investments", "deployments", "tariffs", "contract_rates", "foreign_repayments"):
                _require(isinstance(getattr(order, key), dict), "Invalid order format.")
            errors = validate_order(game, f, order)
            if allow_invalid_drafts and f not in game.submitted:
                # Oversubscribed drafts must survive recovery. Structural/type
                # errors and invalid commitments are still rejected.
                errors = [e for e in errors if not e.startswith(("Deployments exceed available", "Investment allocations exceed"))]
            _require(not errors, f"Invalid {f} orders: {' '.join(errors)}")
        _require(isinstance(game.history, list) and len(game.history) <= 250, "Invalid history.")
        for entry in game.history:
            _require(set(entry) == {"year", "round", "nations"} and type(entry["year"]) is int and type(entry["round"]) is int and set(entry["nations"]) == set(FACTIONS), "Invalid history entry.")
            for values in entry["nations"].values():
                _require(set(values) == {"gdp", "currency", "debt", "content", "innovation", "military", "influence", "energy", "minerals"} and all(number(v) for v in values.values()), "Invalid history metrics.")
        _require(isinstance(game.reports, list) and len(game.reports) <= 100, "Invalid reports.")
        for report in game.reports:
            required = {"round", "year", "messages", "ledgers"}
            _require(set(report) in (required, required | {"phase_ends", "highlights"}) and type(report["year"]) is int and type(report["round"]) is int, "Invalid turn report.")
            _require(isinstance(report["messages"], list) and len(report["messages"]) <= 10000 and all(isinstance(s, str) and len(s) <= 2000 for s in report["messages"]), "Invalid turn messages.")
            _require(set(report["ledgers"]) == set(FACTIONS) and all(isinstance(v, dict) and all(number(x, -1e12, 1e12) for x in v.values()) for v in report["ledgers"].values()), "Invalid ledger.")
            if "phase_ends" in report:
                ends = report["phase_ends"]
                _require(isinstance(ends, dict) and list(ends) == list(PHASES), "Invalid resolution phases.")
                values = list(ends.values())
                _require(all(type(v) is int and 0 <= v <= len(report["messages"]) for v in values)
                    and values == sorted(values) and values[-1] == len(report["messages"]), "Invalid resolution phase bounds.")
                highlights = report["highlights"]
                _require(isinstance(highlights, dict) and set(highlights) == set(FACTIONS), "Invalid turn highlights.")
                _require(all(isinstance(v, list) and len(v) <= 3 and all(type(i) is int and 0 <= i < len(report["messages"]) for i in v) for v in highlights.values()), "Invalid turn highlight indices.")
        return game
    except (TypeError, KeyError, AttributeError, OverflowError, RecursionError, UnicodeError) as exc:
        raise ValueError("Malformed save file.") from exc
