"""Draft editing helpers; never change the resolved world."""

from copy import copy, deepcopy
from dataclasses import asdict

from .catalog import FACTIONS
from .engine import fresh_order
from .forecast import forecast_round
from .rules import INVESTMENTS


class DraftHistory:
    def __init__(self, game):
        self.round = game.round
        self.last = deepcopy(game.orders)
        self.undo = {f: [] for f in FACTIONS}
        self.remembered = {}

    def record(self, game, faction):
        if game.orders[faction] != self.last[faction]:
            self.undo[faction].append(self.last[faction])
            self.undo[faction] = self.undo[faction][-50:]
            self.last[faction] = deepcopy(game.orders[faction])
            return True
        return False

    def restore(self, game, faction):
        if faction in game.submitted or not self.undo[faction]:
            return False
        game.orders[faction] = deepcopy(self.undo[faction].pop())
        self.last[faction] = deepcopy(game.orders[faction])
        return True

    def remember(self, game, faction):
        if faction not in game.submitted:
            self.remembered[faction] = deepcopy(game.orders[faction])

    def restore_remembered(self, game, faction):
        if faction in game.submitted or faction not in self.remembered:
            return False
        game.orders[faction] = deepcopy(self.remembered[faction])
        return self.record(game, faction)


def compare_draft(game, faction, remembered):
    """Re-evaluate both alternatives against the same current world and rivals."""
    result = {}
    for name, order in (("current", game.orders[faction]), ("remembered", remembered)):
        candidate = copy(game)
        candidate.orders = dict(game.orders)
        candidate.orders[faction] = deepcopy(order)
        try:
            result[name] = {"forecast": forecast_round(candidate), "error": None}
        except ValueError as exc:
            result[name] = {"forecast": None, "error": str(exc)}
    return result


def changed_decisions(game, faction):
    baseline = asdict(fresh_order(game, faction))
    current = asdict(game.orders[faction])
    rows = []
    for field, value in current.items():
        before = baseline[field]
        if isinstance(value, dict):
            for name in dict.fromkeys([*before, *value]):
                old, new = before.get(name, 0), value.get(name, 0)
                if old != new:
                    label = INVESTMENTS[name].name if field == "investments" else name
                    rows.append(f"{field.replace('_', ' ').capitalize()} · {label}: {old:g} → {new:g}")
        elif isinstance(value, list):
            if set(value) != set(before):
                rows.append(f"{field.replace('_', ' ').capitalize()}: {', '.join(before) or 'none'} → {', '.join(value) or 'none'}")
        elif value != before:
            rows.append(f"{field.replace('_', ' ').capitalize()}: {before} → {value}")
    return rows
