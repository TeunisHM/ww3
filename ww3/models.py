"""Serializable state; the UI never owns the simulation rules."""

from dataclasses import asdict, dataclass, field
from .catalog import FACTIONS, FRONTS
from .rules import Rules

RULES_VERSION = "1"


def pair(a: str, b: str) -> str:
    return "|".join(sorted((a, b)))


@dataclass
class Order:
    tax_rate: float = .25
    government: str = "Democratic/pluralistic"
    investments: dict[str, float] = field(default_factory=dict)
    deployments: dict[str, float] = field(default_factory=lambda: dict.fromkeys(FRONTS, 0.0))
    tariffs: dict[str, float] = field(default_factory=dict)
    trade_offers: list[str] = field(default_factory=list)
    alliance_offers: list[str] = field(default_factory=list)
    share_bonus: list[str] = field(default_factory=list)
    improve_relations: list[str] = field(default_factory=list)
    foreign_aid: list[str] = field(default_factory=list)
    contract_rates: dict[str, float] = field(default_factory=dict)
    foreign_repayments: dict[str, float] = field(default_factory=dict)
    domestic_repayment: float = 0.0


@dataclass
class Nation:
    id: str
    government: str
    currency: float
    gdp: float
    tax_rate: float
    domestic_debt: float
    military: float
    buildings: dict[str, int]
    military_capacity: float = 0.0
    civic_support: float = 0.0
    content: float = 65.0
    innovation: float = 10.0
    energy: float = 20.0
    minerals: float = 20.0
    compute: float = 0.0
    productivity: float = 0.0
    relations: dict[str, float] = field(default_factory=dict)
    tariffs: dict[str, float] = field(default_factory=dict)
    deployments: dict[str, float] = field(default_factory=lambda: dict.fromkeys(FRONTS, 0.0))
    progress: dict[str, float] = field(default_factory=dict)
    share_bonus: list[str] = field(default_factory=list)
    transition_target: str | None = None
    transition_remaining: int = 0
    last_ledger: dict[str, float] = field(default_factory=dict)
    last_production: dict[str, float] = field(default_factory=dict)


@dataclass
class Contract:
    id: str
    borrower: str
    lender: str
    principal: float
    rate: float
    matures_round: int


@dataclass
class Front:
    name: str
    influence: dict[str, float] = field(default_factory=lambda: dict.fromkeys(FACTIONS, 0.0))
    status: str = "Uncommitted"


@dataclass
class Game:
    nations: dict[str, Nation]
    contracts: list[Contract]
    fronts: dict[str, Front]
    orders: dict[str, Order]
    rules: Rules = field(default_factory=Rules)
    round: int = 1
    mode: str = "solo"
    player: str = "EU"
    trades: list[str] = field(default_factory=list)
    alliances: list[str] = field(default_factory=list)
    submitted: list[str] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
    reports: list[dict] = field(default_factory=list)
    winners: list[str] = field(default_factory=list)
    objective_streaks: dict[str, int] = field(default_factory=lambda: dict.fromkeys(FACTIONS, 0))

    @property
    def winner(self) -> str | None:
        return self.winners[0] if len(self.winners) == 1 else None

    @property
    def year(self) -> int:
        return self.rules.start_year + self.round - 1

    def to_dict(self) -> dict:
        return {"schema_version": 3, "rules_version": RULES_VERSION, **asdict(self)}

    def debt(self, faction: str) -> float:
        return self.nations[faction].domestic_debt + sum(c.principal for c in self.contracts if c.borrower == faction)

    def influence(self, faction: str) -> float:
        return sum(f.influence[faction] for f in self.fronts.values())
