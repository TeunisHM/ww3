"""Construction information from the same committed state used by the engine.

Allocations in an order are a draft. ``committed`` must be the result of
``engine._prepare`` for that draft; it has paid for new work and applied all
completions, but has not yet run the year's economy. Without a valid committed
state, only existing facilities, carried work and draft allocations are known.
"""

from collections import Counter
from collections.abc import Iterable

from ww3.core.engine import EPS, investment_cost
from ww3.core.models import Game
from ww3.core.rules import BUILDINGS, INVESTMENTS


def construction_rows(
    game: Game,
    faction: str,
    committed: Game | None = None,
    messages: Iterable[str] = (),
) -> list[dict]:
    """Describe every building and repeatable project without resolving orders.

    Progress values are fractions of one unit. ``remaining_work`` is the work
    to finish the current unit (or start and finish one if none is underway).
    ``expected_remaining_work`` concerns only unfinished work after the draft,
    so it is zero when all allocated work finishes whole units.

    Future values are ``None`` when the plan has not been validated. For a
    validated plan, use the committed treaty state for work costs, and the
    engine's completion messages to count repeatable projects, which have no
    persistent facility count. This also preserves the engine's EPS rounding.
    """
    nation = game.nations[faction]
    planned = committed.nations[faction] if committed is not None else None
    completions = Counter(messages)
    rows = []
    for key, spec in INVESTMENTS.items():
        is_building = key in BUILDINGS
        work_per_unit = investment_cost(committed or game, faction, key)["productivity"]
        current_progress = nation.progress.get(key, 0.0)
        allocated_work = game.orders[faction].investments.get(key, 0.0)
        expected_progress = planned.progress.get(key, 0.0) if planned is not None else None
        completed = None
        started = None
        expected_remaining_work = None
        if planned is not None:
            completed = (
                planned.buildings[key] - nation.buildings[key]
                if is_building
                else completions[f"{faction} completed {spec.name.lower()}."]
            )
            # A carried unit is already paid unless the engine treats its work
            # as zero. Any new unfinished tail has also incurred startup costs.
            started = (
                completed + int(expected_progress > 0) - int(current_progress > EPS)
                if allocated_work > EPS else 0
            )
            expected_remaining_work = (
                max(0.0, (1 - expected_progress) * work_per_unit)
                if expected_progress else 0.0
            )
        rows.append({
            "key": key,
            "name": spec.name,
            "kind": "building" if is_building else "project",
            "current_count": nation.buildings[key] if is_building else None,
            "current_progress": current_progress,
            "allocated_work": allocated_work,
            "work_per_unit": work_per_unit,
            "remaining_work": max(0.0, (1 - current_progress) * work_per_unit),
            "completed": completed,
            "started": started,
            "forecast_valid": planned is not None,
            "expected_count": planned.buildings[key] if planned is not None and is_building else None,
            "expected_progress": expected_progress,
            "expected_remaining_work": expected_remaining_work,
        })
    return rows
