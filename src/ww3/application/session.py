"""Client-independent campaign commands. Only this layer advances a client game."""

from copy import deepcopy
from dataclasses import asdict, dataclass

from ww3.core.ai import prepare_ai_orders
from ww3.core.catalog import FACTIONS
from ww3.core.engine import fresh_order, new_game, preview_plan, resolve_round
from ww3.core.forecast import forecast_round
from ww3.core.models import Game, Order
from ww3.persistence import dumps, loads
from .planning import DraftHistory, compare_draft


class SessionError(ValueError):
    """A command is incompatible with the current campaign state."""


class RevisionConflict(SessionError):
    """The caller edited an obsolete snapshot."""


@dataclass(frozen=True)
class TurnResult:
    resolved: bool
    next_commander: str
    new_victory: bool = False


class GameSession:
    def __init__(self, game: Game):
        self._game = deepcopy(game)
        self._history = DraftHistory(self._game)
        self.revision = 0

    @classmethod
    def new(cls, mode="solo", player="EU", rules=None):
        if mode not in ("solo", "hotseat", "sandbox") or player not in FACTIONS:
            raise SessionError("Unknown game mode or player.")
        game = new_game(mode, player, rules)
        # Use the same scenario validation as portable saves.
        return cls(loads(dumps(game), allow_invalid_drafts=True))

    def snapshot(self) -> Game:
        """Callers may edit their copy, then submit an order explicitly."""
        return deepcopy(self._game)

    @property
    def draft_history(self):
        return deepcopy(self._history)

    def check_revision(self, expected):
        if type(expected) is not int or expected != self.revision:
            raise RevisionConflict(f"Expected revision {self.revision}; refresh the campaign before editing.")

    def _editable(self, faction):
        if faction not in FACTIONS:
            raise SessionError("Unknown faction.")
        if self._game.mode == "solo" and faction != self._game.player:
            raise SessionError("Computer opponents own these orders.")
        if faction in self._game.submitted:
            raise SessionError("These orders are committed. Reopen them before editing.")

    def replace_order(self, faction: str, order: Order) -> bool:
        self._editable(faction)
        candidate = self.snapshot()
        candidate.orders[faction] = deepcopy(order)
        # Permit oversubscribed drafts, but reject malformed fields/values using
        # the existing save contract. A failed edit never changes this session.
        validated = loads(dumps(candidate), allow_invalid_drafts=True)
        if validated.orders[faction] == self._game.orders[faction]:
            return False
        self._game.orders[faction] = validated.orders[faction]
        self._history.record(self._game, faction)
        self.revision += 1
        return True

    def edit_order(self, faction: str, changes: dict) -> bool:
        """Patch top-level order fields; dictionary fields replace that map."""
        self._editable(faction)
        data = asdict(self._game.orders[faction])
        if not isinstance(changes, dict) or not set(changes) <= set(data):
            raise SessionError("Unknown order field.")
        data.update(deepcopy(changes))
        return self.replace_order(faction, Order(**data))

    def undo(self, faction) -> bool:
        self._editable(faction)
        changed = self._history.restore(self._game, faction)
        self.revision += int(changed)
        return changed

    def reset_draft(self, faction) -> bool:
        self._editable(faction)
        return self.replace_order(faction, fresh_order(self._game, faction))

    def remember(self, faction):
        self._editable(faction)
        self._history.remember(self._game, faction)
        self.revision += 1

    def restore_remembered(self, faction) -> bool:
        self._editable(faction)
        changed = self._history.restore_remembered(self._game, faction)
        self.revision += int(changed)
        return changed

    def compare(self, faction):
        if faction not in self._history.remembered:
            raise SessionError("No remembered draft for this faction.")
        return compare_draft(self._game, faction, self._history.remembered[faction])

    def forecast(self):
        return forecast_round(self._game)

    def commit(self, faction) -> TurnResult:
        """Commit one hotseat faction, or atomically resolve all ready orders."""
        self._editable(faction)
        preview_plan(self._game, faction)
        if self._game.mode == "hotseat" and len(self._game.submitted) < len(FACTIONS) - 1:
            self._game.submitted.append(faction)
            self.revision += 1
            return TurnResult(False, next(f for f in FACTIONS if f not in self._game.submitted))
        # AI preparation and resolution work on copies. Failures leave the
        # world, submissions, undo history, and revision intact.
        resolved = resolve_round(prepare_ai_orders(self._game))
        result = TurnResult(True, resolved.player, bool(resolved.winners and not self._game.winners))
        self._game = resolved
        self._history = DraftHistory(resolved)
        self.revision += 1
        return result

    def reopen(self, faction):
        if self._game.mode != "hotseat" or faction not in self._game.submitted:
            raise SessionError("This faction has no committed hotseat orders.")
        self._game.submitted.remove(faction)
        self.revision += 1

    def load(self, payload):
        game = loads(payload, allow_invalid_drafts=True)
        self._game = game
        self._history = DraftHistory(game)
        self.revision += 1

    def export(self):
        return dumps(self._game)
