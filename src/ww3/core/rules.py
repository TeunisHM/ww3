"""Explicit, adjustable defaults for gaps in the original design.

All original numeric building costs and outputs are preserved in BUILDINGS.
DESIGN.md is the authoritative gameplay specification.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Building:
    name: str
    description: str
    currency: float = 0.0
    minerals: float = 0.0
    productivity: float = 10.0
    energy_upkeep: float = 0.0
    compute_upkeep: float = 0.0
    currency_upkeep: float = 0.0
    mineral_upkeep: float = 0.0
    added_rule: bool = False


BUILDINGS = {
    "renewable": Building("Renewable facility", "Energy: 5 + 0.1 × innovation / year", .5, 5, currency_upkeep=.1),
    "thermal": Building("Thermal plant", "Energy: 5 / year", 1, mineral_upkeep=.1),
    "datacenter": Building("Data center", "Compute: 10 / year; innovation: +1 on completion", 2.0, 2, energy_upkeep=1),
    "drone": Building("Drone facility", "Military: 10 × (1 + innovation / 100) / year", minerals=3, energy_upkeep=3),
    "cyber": Building("Cyber warfare lab", "Military: 5 + 0.1 × innovation / year", .5, compute_upkeep=5),
    "mine": Building("Mineral mine", "Minerals: 5 / year; permanent −1 content in the content formula", .5, 3),
    "factory": Building("Factory", "Productivity capacity: +5 / year before modifiers", 1.0, currency_upkeep=.1),
    "research": Building("Research lab", "Innovation depends on citizen content", .75, 2, energy_upkeep=1, compute_upkeep=5, currency_upkeep=.1, added_rule=True),
}

PROJECTS = {
    "research_grant": Building("Research program", "+2 innovation, modified by content and national traits", .2, compute_upkeep=5, added_rule=True),
    "civil_investment": Building("Public services", "+3 citizen content", .25, added_rule=True),
    "infrastructure": Building("Infrastructure program", "+0.25 T GDP", .5, 1, productivity=20, added_rule=True),
    "modernization": Building("Military modernization", "+10 military, modified by innovation", .25, 2, energy_upkeep=3, added_rule=True),
}
INVESTMENTS = {**BUILDINGS, **PROJECTS}


def starting_buildings():
    return {
        "EU": dict(renewable=3, thermal=2, datacenter=4, drone=1, cyber=1, mine=2, factory=0, research=2),
        "US": dict(renewable=3, thermal=4, datacenter=6, drone=3, cyber=3, mine=3, factory=0, research=3),
        "China": dict(renewable=3, thermal=5, datacenter=4, drone=3, cyber=2, mine=4, factory=0, research=2),
        "Russia": dict(renewable=1, thermal=3, datacenter=1, drone=2, cyber=1, mine=4, factory=0, research=1),
    }


def starting_deployments():
    from ww3.core.catalog import FRONTS
    return {f: dict(zip(FRONTS, values)) for f, values in {
        "EU": (60.0, 0.0, 20.0, 0.0), "US": (0.0, 140.0, 60.0, 60.0),
        "China": (0.0, 110.0, 30.0, 10.0), "Russia": (80.0, 0.0, 50.0, 10.0),
    }.items()}


def starting_influence():
    from ww3.core.catalog import FACTIONS, FRONTS
    return {front: dict(zip(FACTIONS, values)) for front, values in zip(FRONTS, (
        (35.0, 0.0, 0.0, 45.0), (0.0, 40.0, 45.0, 0.0),
        (10.0, 25.0, 15.0, 30.0), (0.0, 60.0, 10.0, 10.0),
    ))}


@dataclass
class Rules:
    start_year: int = 2026
    starting_capital: dict = field(default_factory=lambda: {"EU": 60.0, "US": 50.0, "China": 40.0, "Russia": 10.0})
    starting_buildings: dict = field(default_factory=starting_buildings)
    starting_energy: dict = field(default_factory=lambda: {"EU": 10.0, "US": 20.0, "China": 15.0, "Russia": 30.0})
    starting_minerals: dict = field(default_factory=lambda: {"EU": 5.0, "US": 5.0, "China": 20.0, "Russia": 10.0})
    starting_content: dict = field(default_factory=lambda: {"EU": 60.0, "US": 75.0, "China": 80.0, "Russia": 74.0})
    starting_innovation: dict = field(default_factory=lambda: {"EU": 5.0, "US": 8.0, "China": 6.0, "Russia": 2.0})
    starting_productivity: dict = field(default_factory=lambda: {"EU": 10.0, "US": 12.0, "China": 15.0, "Russia": 8.0})
    starting_deployments: dict = field(default_factory=starting_deployments)
    starting_influence: dict = field(default_factory=starting_influence)
    factory_output: float = 5.0
    combat_attrition: float = .10
    combat_base_decay: float = .01
    reserve_recovery: float = .01
    influence_gain: float = 10.0
    hostility_drift: float = .02
    government_transition_years: int = 3
    transition_unrest: float = 5.0
    contract_years: int = 3
    foreign_interest: float = .04
    domestic_base_interest: float = .05
    domestic_discontent_interest: float = .10
    military_upkeep: float = .005
    trade_volume: float = .015
    luxury_export_rate: float = .01
    diplomacy_cost: float = .1
    diplomacy_gain: float = .2
    foreign_aid_amount: float = 1.0
    foreign_aid_relation_gain: float = .25
    trade_relation_gain: float = .08
    tariff_relation_penalty: float = .3
    conflict_relation_penalty: float = .15
    war_discontent: float = 1.5
    victory_mode: str = "objectives"
    objective_hold_years: int = 3
    victory_target: float = 0.0
    ai_seed: int = 17


GOVERNMENT_EFFECTS = {
    "Democratic/pluralistic": {"innovation": 1.10, "productivity": 1.0, "content": 1.0},
    "Democratic/oligarchic": {"innovation": 1.05, "productivity": 1.0, "content": 0.0},
    "Authoritarian/one-party": {"innovation": 1.0, "productivity": 1.10, "content": -.5},
    "Authoritarian/dictator": {"innovation": .95, "productivity": 1.05, "content": -1.0},
}
