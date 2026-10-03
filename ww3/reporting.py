"""Explanations recorded at the actual engine phase boundaries.

Message indices keep reports small and make every headline traceable to a phase.
This module observes resolution; it never applies gameplay effects.
"""

from .catalog import FACTIONS, FRONTS
from .strategy import objective_progress

PHASES = {
    "orders": "Treaties & orders",
    "economy": "Economy & shortages",
    "relations": "Relations",
    "combat": "Combat & territorial influence",
    "society": "Society",
    "objectives": "Objective progress",
}


class TurnReport:
    def __init__(self, opening, messages):
        self.opening = opening
        self.messages = messages
        self.phase_ends = {}
        self.candidates = {f: [] for f in FACTIONS}

    def add(self, faction, phase, text, weight=0):
        index = len(self.messages)
        self.messages.append(f"{faction}: {text}")
        self.candidates[faction].append((weight, index))

    def finish(self, phase):
        self.phase_ends[phase] = len(self.messages)

    def orders(self, game, ledgers):
        for f in FACTIONS:
            o = game.orders[f]
            spending = -ledgers[f]["planned_spending"]
            self.add(f, "orders", f"Orders used {sum(o.investments.values()):.1f} productivity and "
                f"{spending:.3f} T from reserves for construction, outreach, aid and principal repayments. "
                "Mutual treaties took effect before construction costs were calculated.", spending / max(1, self.opening.nations[f].currency) * 30)
        self.finish("orders")

    def economy(self, game):
        for f in FACTIONS:
            n = game.nations[f]
            ledger, prod = n.last_ledger, n.last_production
            delta = n.currency - self.opening.nations[f].currency
            flows = {k: v for k, v in ledger.items() if k not in
                ("opening_currency", "closing_currency", "operating_balance", "new_borrowing")}
            causes = sorted(flows, key=lambda k: abs(flows[k]), reverse=True)[:3]
            explanation = ", ".join(f"{k.replace('_', ' ')} {flows[k]:+.3f} T" for k in causes)
            shortage = min(prod[k] for k in ("energy_supply", "compute_supply", "thermal_supply"))
            self.add(f, "economy", f"Treasury {delta:+.3f} T → {n.currency:.3f} T. Largest cash flows: {explanation}. "
                f"New borrowing {ledger['new_borrowing']:.3f} T. "
                f"Facility operation: energy {prod['energy_supply']:.0%}, compute {prod['compute_supply']:.0%}, fuel {prod['thermal_supply']:.0%}.",
                abs(delta) / max(1, self.opening.nations[f].currency) * 40 + (1 - shortage) * 100 + (50 if ledger['new_borrowing'] else 0))
        self.finish("economy")

    def relations(self, game, before):
        for f in FACTIONS:
            changes = {other: game.nations[f].relations[other] - value for other, value in before[f].items()}
            summary = ", ".join(f"{other} {delta:+.3f} → {game.nations[f].relations[other]:.3f}" for other, delta in changes.items())
            self.add(f, "relations", f"Annual relationship changes: {summary}. "
                "Active trade, tariffs, outreach and aid offset or add to annual deterioration. "
                "Debt renewal changes occurred with orders; conflict penalties follow in combat.", max(abs(v) for v in changes.values()) * 35)
        self.finish("relations")

    def combat(self, game, deployed):
        for f in FACTIONS:
            losses = {front: deployed[f][front] - game.nations[f].deployments[front] for front in FRONTS}
            total = sum(losses.values())
            fronts = "; ".join(f"{name}: lost {losses[name]:.2f} power, influence "
                f"{game.fronts[name].influence[f] - self.opening.fronts[name].influence[f]:+.2f} → {game.fronts[name].influence[f]:.2f}/100"
                for name in FRONTS if deployed[f][name] or game.fronts[name].influence[f] != self.opening.fronts[name].influence[f])
            self.add(f, "combat", f"Combat losses {total:.2f} power. {fronts or 'No deployed forces or influence changes'}. "
                "Losses use opposing coalition strengths; only a sole surviving coalition gains influence. "
                "Production and reserve recovery were applied in the economy phase.", total / max(1, self.opening.nations[f].military) * 150
                + abs(game.influence(f) - self.opening.influence(f)))
        self.finish("combat")

    def society(self, game):
        for f in FACTIONS:
            old, n = self.opening.nations[f], game.nations[f]
            self.add(f, "society", f"Citizen content {old.content:.1f} → {n.content:.1f}; GDP {old.gdp:.3f} → {n.gdp:.3f} T "
                f"(annual growth {n.last_production['gdp_growth']:+.2%}). "
                "Content reflects taxes, deployments, mines, conflict, government, shortages, innovation and public services. "
                "Growth uses pre-update content, innovation, taxes, conflict and energy supply.", abs(n.content - old.content))
        self.finish("society")

    def objectives(self, game):
        for f in FACTIONS:
            progress = objective_progress(game, f)
            previous, streak = self.opening.objective_streaks[f], game.objective_streaks[f]
            conditions = "; ".join(f"{'Met' if p['met'] else 'Unmet'} — {p['condition']}: {p['current']}" for p in progress)
            self.add(f, "objectives", f"Objective hold {previous} → {streak}/{game.rules.objective_hold_years} consecutive years. "
                f"Checked after combat and society: {conditions}. "
                + ("A missing condition resets the hold." if not all(p['met'] for p in progress) else "All conditions hold this year.")
                + (f" Victory mode is {game.rules.victory_mode}; faction holds are reference only." if game.rules.victory_mode != "objectives" else ""),
                100 if previous != streak else 5)
        self.finish("objectives")

    def metadata(self):
        return {"phase_ends": self.phase_ends, "highlights": {
            f: [index for _, index in sorted(values, key=lambda v: (-v[0], v[1]))[:3]]
            for f, values in self.candidates.items()}}


def phase_messages(report, phase):
    """Older saves retain their original chronicle without invented phase data."""
    if "phase_ends" not in report:
        return []
    start = 0
    for name, end in report["phase_ends"].items():
        if name == phase:
            return report["messages"][start:end]
        start = end
    return []


def message_phase(report, index):
    return next((phase for phase, end in report.get("phase_ends", {}).items() if index < end), None)
