"""Military shares, allied coalitions, and the objectives in DESIGN.md."""

from ww3.core.catalog import FACTIONS, FRONTS
from ww3.core.models import Game, pair

EPS = 1e-8


def coalitions(game: Game, front: str) -> list[list[str]]:
    active = [f for f in FACTIONS if game.nations[f].deployments[front] > EPS]
    groups = []
    while active:
        group = [active.pop(0)]
        changed = True
        while changed:
            changed = False
            for f in list(active):
                if any(pair(f, ally) in game.alliances for ally in group):
                    group.append(f)
                    active.remove(f)
                    changed = True
        groups.append(group)
    return groups


def dominance(game: Game, front: str) -> dict[str, float]:
    total = sum(n.deployments[front] for n in game.nations.values())
    return {f: game.nations[f].deployments[front] / total if total > EPS else 0.0 for f in FACTIONS}


def dominance_bonus(game: Game, faction: str) -> float:
    bonus = 0.0
    for front in FRONTS:
        share = dominance(game, front)[faction]
        bonus += .15 if share >= .75 - EPS else .10 if share >= .50 - EPS else .05 if share >= .25 - EPS else 0.0
    return bonus


def theater_snapshot(game: Game, front: str) -> dict:
    """Public theater facts, shared by the map and exact forecasts."""
    shares = dominance(game, front)
    return {
        "status": game.fronts[front].status,
        "coalitions": [{"members": group, "strength": sum(game.nations[f].deployments[front] for f in group)}
            for group in coalitions(game, front)],
        "factions": {f: {"deployed": game.nations[f].deployments[front], "share": shares[f],
            "influence": game.fronts[front].influence[f],
            "upkeep": game.nations[f].deployments[front] * game.rules.military_upkeep} for f in FACTIONS},
    }


OBJECTIVE_NAMES = {
    "EU": "European security & Arctic balance",
    "US": "Monroe doctrine & Arctic dominance",
    "China": "Pacific & Arctic dominance",
    "Russia": "Eurasian & Arctic dominance",
}


def _objective(condition, current, detail, front, value, target, comparison, unit="share"):
    """Keep displayed targets and objective decisions on the same values."""
    met = (value >= target - EPS if comparison == ">=" else
           value <= target + EPS if comparison == "<=" else value > target + EPS)
    return {"condition": condition, "current": current, "met": met, "detail": detail,
            "front": front, "value": value, "target": target, "comparison": comparison, "unit": unit}


def objective_progress(game: Game, faction: str) -> list[dict]:
    east, pacific, arctic, south = FRONTS
    eastern = dominance(game, east)
    polar = dominance(game, arctic)
    sea = dominance(game, pacific)
    if faction == "EU":
        group = next((g for g in coalitions(game, east) if "EU" in g), [])
        security_share = sum(eastern[f] for f in group) if "Russia" not in group else 0.0
        influence = game.fronts[east].influence["Russia"]
        foreign_share = max(polar[f] for f in FACTIONS if f != "EU")
        return [
            _objective("EU security coalition holds ≥60% of Eastern Europe", f"{security_share:.1%}",
                "EU must deploy forces. Connected allies present count; a coalition containing Russia cannot satisfy this condition.",
                east, security_share, .60, ">="),
            _objective("Russian current influence in Eastern Europe ≤10/100", f"{influence:.1f}/100",
                "Territorial influence can be displaced, so early Russian gains do not permanently block victory.",
                east, influence, 10, "<=", "influence"),
            _objective("No other faction has >40% military share in the Arctic", f"Largest foreign share: {foreign_share:.1%}",
                "This includes allies. An empty Arctic counts as neutral.", arctic, foreign_share, .40, "<="),
        ]
    if faction == "US":
        foreign = sum(game.nations[f].deployments[south] for f in FACTIONS if f != "US")
        return [
            _objective("No foreign military presence in South America", f"{foreign:.1f} foreign power",
                "All foreign factions count, including allies. An empty theater satisfies this condition.", south, foreign, 0, "<=", "power"),
            _objective("US military share in the Arctic ≥80%", f"{polar['US']:.1%}",
                "Measured using US forces only.", arctic, polar["US"], .8, ">="),
            _objective("Chinese military share in the Pacific ≤50%", f"{sea['China']:.1%}",
                "An empty Pacific satisfies this ceiling.", pacific, sea["China"], .5, "<="),
        ]
    if faction == "China":
        return [
            _objective("Chinese military share in the Pacific >80%", f"{sea['China']:.1%}",
                "Strictly above 80%; Chinese forces only.", pacific, sea["China"], .8, ">"),
            _objective("Chinese military share in the Arctic ≥80%", f"{polar['China']:.1%}",
                "Chinese forces only.", arctic, polar["China"], .8, ">="),
        ]
    return [
        _objective("Russian military share in Eastern Europe ≥99%", f"{eastern['Russia']:.1%}",
            "Russian forces only.", east, eastern["Russia"], .99, ">="),
        _objective("Russian military share in the Arctic ≥50%", f"{polar['Russia']:.1%}",
            "Russian forces only.", arctic, polar["Russia"], .5, ">="),
    ]


def update_victory(game: Game, messages: list[str]):
    for f in FACTIONS:
        met = all(item["met"] for item in objective_progress(game, f))
        game.objective_streaks[f] = min(game.rules.objective_hold_years, game.objective_streaks[f] + 1) if met else 0
    if game.winners or game.rules.victory_mode == "open":
        return
    winners = []
    if game.rules.victory_mode == "objectives":
        winners = [f for f in FACTIONS if game.objective_streaks[f] >= game.rules.objective_hold_years]
    elif game.rules.victory_mode == "influence":
        best = max(game.influence(f) for f in FACTIONS)
        if best >= game.rules.victory_target:
            winners = [f for f in FACTIONS if abs(game.influence(f) - best) <= EPS]
    if winners:
        game.winners = winners
        messages.append(f"Victory declared: {' + '.join(winners)}. You may continue the simulation.")
