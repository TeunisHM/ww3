from copy import deepcopy
import json
import math

import pytest

from ww3.ai import prepare_ai_orders
from ww3.catalog import FACTIONS, FRONTS, GOVERNMENTS, SCENARIO
from ww3.engine import InvalidOrder, compute_multiplier, investment_cost, new_game as scenario_game, preview_plan, resolve_round
from ww3.models import pair
from ww3.persistence import dumps, loads
from ww3.rules import BUILDINGS, Rules


def new_game(**kwargs):
    """Isolate economic and combat units from the contested opening scenario."""
    game = scenario_game(**kwargs)
    for f in FACTIONS:
        game.nations[f].deployments = dict.fromkeys(FRONTS, 0.0)
        game.orders[f].deployments = dict.fromkeys(FRONTS, 0.0)
    for front in game.fronts.values():
        front.influence = dict.fromkeys(FACTIONS, 0.0)
        front.status = "Uncommitted"
    return game


def invariant(game):
    for f, n in game.nations.items():
        for field in ("currency", "gdp", "domestic_debt", "military", "energy", "minerals", "compute", "productivity", "innovation"):
            assert math.isfinite(getattr(n, field)) and getattr(n, field) >= 0, (f, field)
        assert 0 <= n.content <= 100
        assert sum(n.deployments.values()) <= n.military + 1e-7
        assert all(0 <= x < 1 for x in n.progress.values())
        for other, relation in n.relations.items():
            assert 1 <= relation <= 5
            assert relation == game.nations[other].relations[f]
    for front in game.fronts.values():
        assert 0 <= sum(front.influence.values()) <= 100 + 1e-7


def test_source_starting_values_and_foreign_debt_conservation():
    game = new_game()
    for f, spec in SCENARIO.items():
        n = game.nations[f]
        assert n.gdp == spec["gdp"]
        assert n.tax_rate == spec["tax_rate"]
        assert n.military == spec["military"]
        assert n.relations == spec["relations"]
        assert game.debt(f) == pytest.approx(spec["debt"])
        assert sum(c.principal for c in game.contracts if c.borrower == f) == pytest.approx(spec["debt"] * (1 - spec["domestic_share"]))
    assert game.nations["EU"].currency == 60
    assert all(c.lender != c.borrower for c in game.contracts)


def test_resolution_does_not_mutate_input_and_is_deterministic():
    game = prepare_ai_orders(new_game())
    before = dumps(game)
    assert resolve_round(game) == resolve_round(game)
    assert dumps(game) == before


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), 99999])
def test_bad_military_orders_are_atomic(value):
    game = new_game()
    game.orders["EU"].deployments[FRONTS[0]] = value
    before = deepcopy(game.nations)
    with pytest.raises(InvalidOrder):
        resolve_round(game)
    assert game.nations == before


def test_overspending_and_overallocating_are_rejected():
    game = new_game()
    game.nations["EU"].currency = 0
    game.orders["EU"].investments = {"factory": 10}
    with pytest.raises(InvalidOrder, match="currency"):
        resolve_round(game)
    game.orders["EU"].investments = {"factory": 1000}
    with pytest.raises(InvalidOrder, match="productivity"):
        resolve_round(game)


def test_partial_build_pays_once_and_preserves_work():
    game = new_game()
    game.orders["EU"].investments = {"factory": 5}
    preview = preview_plan(game, "EU")
    assert preview["spending"] == pytest.approx(investment_cost(game, "EU", "factory")["currency"])
    one = resolve_round(game)
    assert one.nations["EU"].progress["factory"] == .5
    assert one.nations["EU"].buildings["factory"] == 0
    two = resolve_round(one)
    assert two.nations["EU"].progress["factory"] == .5
    two.orders["EU"].investments = {"factory": 5}
    assert preview_plan(two, "EU")["spending"] == 0
    three = resolve_round(two)
    assert "factory" not in three.nations["EU"].progress
    assert three.nations["EU"].buildings["factory"] == 1


def test_multiple_completions_and_repeatable_projects():
    game = new_game()
    game.nations["EU"].productivity = 30
    game.orders["EU"].investments = {"factory": 20, "civil_investment": 10}
    resolved = resolve_round(game)
    assert resolved.nations["EU"].buildings["factory"] == 2
    assert resolved.nations["EU"].content > resolve_round(new_game()).nations["EU"].content


def test_capacities_reset_while_stocks_accumulate():
    first = resolve_round(new_game())
    second = resolve_round(first)
    a, b = first.nations["EU"], second.nations["EU"]
    assert a.compute == b.compute
    assert a.productivity == b.productivity
    assert b.energy > a.energy
    assert b.minerals > a.minerals
    assert b.innovation > a.innovation


def test_zero_power_suspends_energy_dependent_production():
    game = new_game()
    n = game.nations["EU"]
    n.energy = 0
    n.buildings["thermal"] = n.buildings["renewable"] = 0
    result = resolve_round(game).nations["EU"]
    assert result.productivity == game.nations["EU"].productivity
    assert result.compute == 0
    assert result.energy == 0
    assert result.last_production["military"] == 0
    assert result.last_production["innovation"] == 0


def test_compute_is_rationed_without_negative_stock():
    game = new_game()
    n = game.nations["EU"]
    n.buildings["datacenter"] = 1
    n.buildings["cyber"] = 8
    result = resolve_round(game).nations["EU"]
    assert result.last_production["compute_supply"] == pytest.approx(.2)
    assert result.compute == 0
    assert result.last_production["military"] == pytest.approx(10.5 + 8 * 5.5 * .2)


def test_foreign_interest_conserves_cash_and_ledger_reconciles():
    game = resolve_round(new_game())
    assert sum(n.last_ledger["foreign_interest"] + n.last_ledger["interest_received"] for n in game.nations.values()) == pytest.approx(0)
    for n in game.nations.values():
        ledger = n.last_ledger
        assert ledger["closing_currency"] == pytest.approx(sum(value for key, value in ledger.items() if key not in ("operating_balance", "closing_currency")))


def test_deficits_issue_only_domestic_debt():
    game = new_game(rules=Rules(military_upkeep=.01))
    game.nations["US"].currency = 0
    game.orders["US"].deployments[FRONTS[0]] = 100
    game.orders["US"].tax_rate = 0
    before = game.nations["US"].domestic_debt
    result = resolve_round(game)
    assert result.nations["US"].currency == 0
    assert result.nations["US"].domestic_debt > before
    assert [c.principal for c in result.contracts] == [c.principal for c in game.contracts]


def test_unilateral_offer_is_pending_then_mutual_trade_activates():
    game = new_game()
    game.orders["US"].trade_offers = ["EU"]
    one = resolve_round(game)
    assert pair("EU", "US") not in one.trades
    one.orders["EU"].trade_offers = ["US"]
    two = resolve_round(one)
    assert pair("EU", "US") in two.trades
    assert investment_cost(two, "US", "datacenter")["productivity"] == 7.5
    two.orders["EU"].trade_offers = []
    assert pair("EU", "US") not in resolve_round(two).trades


def test_shared_compute_and_productivity_require_consent():
    game = new_game()
    for other in ("US", "China"):
        game.orders["EU"].trade_offers.append(other)
        game.orders[other].trade_offers = ["EU"]
    no_share = resolve_round(game)
    assert compute_multiplier(no_share, "EU") == 1
    game.orders["US"].share_bonus = ["EU"]
    game.orders["China"].share_bonus = ["EU"]
    shared = resolve_round(game)
    assert compute_multiplier(shared, "EU") == .8
    assert shared.nations["EU"].productivity == pytest.approx(no_share.nations["EU"].productivity * 1.2)
    assert shared.nations["EU"].compute > no_share.nations["EU"].compute


def test_preview_honors_pending_shared_trade_benefits():
    game = new_game(mode="sandbox")
    game.nations["EU"].compute = 4
    game.orders["EU"].trade_offers = ["US"]
    game.orders["US"].trade_offers = ["EU"]
    game.orders["US"].share_bonus = ["EU"]
    game.orders["EU"].investments = {"research_grant": 10}
    assert preview_plan(game, "EU")["compute"] == 0
    assert resolve_round(game).round == 2


def test_simultaneous_resolution_is_independent_of_faction_iteration_order():
    game = prepare_ai_orders(new_game())
    reordered = deepcopy(game)
    reordered.nations = dict(reversed(list(reordered.nations.items())))
    assert resolve_round(game) == resolve_round(reordered)


def test_tariffs_reduce_trade_and_relations():
    game = new_game()
    game.orders["EU"].trade_offers = ["US"]
    game.orders["US"].trade_offers = ["EU"]
    free = resolve_round(game)
    game.orders["EU"].tariffs["US"] = .5
    duty = resolve_round(game)
    assert duty.nations["EU"].last_ledger["tariff_income"] > 0
    assert duty.nations["EU"].last_ledger["trade_income"] < free.nations["EU"].last_ledger["trade_income"]
    assert duty.nations["EU"].relations["US"] < free.nations["EU"].relations["US"]


def test_aid_is_a_real_cash_transfer_and_improves_relations():
    game = new_game()
    game.orders["EU"].foreign_aid = ["Russia"]
    result = resolve_round(game)
    baseline = resolve_round(new_game())
    assert result.nations["EU"].currency == pytest.approx(baseline.nations["EU"].currency - 1)
    assert result.nations["Russia"].currency == pytest.approx(baseline.nations["Russia"].currency + 1)
    assert result.nations["Russia"].relations["EU"] == pytest.approx(baseline.nations["Russia"].relations["EU"] + .25)
    for n in result.nations.values():
        assert n.currency == pytest.approx(sum(v for k, v in n.last_ledger.items() if k not in ("operating_balance", "closing_currency")))


def test_government_transition_takes_three_years_and_causes_unrest():
    game = new_game()
    game.orders["EU"].government = GOVERNMENTS[3]
    first = resolve_round(game)
    assert first.nations["EU"].government == GOVERNMENTS[0]
    assert first.nations["EU"].transition_remaining == 2
    assert first.nations["EU"].content < resolve_round(new_game()).nations["EU"].content
    second = resolve_round(first)
    assert second.nations["EU"].transition_remaining == 1
    third = resolve_round(second)
    assert third.nations["EU"].government == GOVERNMENTS[3]
    assert third.nations["EU"].transition_target is None


def test_contract_terms_locked_until_maturity_and_controlled_by_lender():
    game = new_game()
    c = next(c for c in game.contracts if c.borrower == "US" and c.lender == "EU")
    game.orders["EU"].contract_rates[c.id] = .08
    with pytest.raises(InvalidOrder, match="lender"):
        resolve_round(game)
    game.round = c.matures_round
    result = resolve_round(game)
    contract = next(x for x in result.contracts if x.id == c.id)
    assert contract.rate == .08 and contract.matures_round == 6
    assert result.nations["US"].relations["EU"] == pytest.approx(4 - .2 - game.rules.hostility_drift)
    game.orders["EU"].contract_rates = {}
    game.orders["US"].contract_rates[c.id] = .08
    with pytest.raises(InvalidOrder):
        resolve_round(game)


def test_principal_repayment_transfers_cash_and_reduces_debt():
    game = new_game()
    game.round = 3
    c = next(c for c in game.contracts if c.borrower == "EU" and c.lender == "US")
    amount = c.principal
    game.orders["EU"].foreign_repayments[c.id] = amount
    result = resolve_round(game)
    assert result.debt("EU") == pytest.approx(game.debt("EU") - amount)
    assert result.nations["US"].last_ledger["principal_received"] == pytest.approx(amount)
    for n in result.nations.values():
        assert n.currency == pytest.approx(sum(v for k, v in n.last_ledger.items() if k not in ("operating_balance", "closing_currency")))


def test_lone_force_and_alliance_share_influence_without_losses():
    game = new_game()
    game.orders["EU"].deployments[FRONTS[0]] = 60
    game.orders["US"].deployments[FRONTS[0]] = 40
    game.orders["EU"].alliance_offers = ["US"]
    game.orders["US"].alliance_offers = ["EU"]
    result = resolve_round(game)
    assert result.fronts[FRONTS[0]].influence["EU"] == 6
    assert result.fronts[FRONTS[0]].influence["US"] == 4
    assert result.nations["EU"].deployments[FRONTS[0]] == 60


def test_coalition_attrition_is_proportional_and_simultaneous():
    game = new_game()
    game.orders["EU"].alliance_offers = ["US"]
    game.orders["US"].alliance_offers = ["EU"]
    for f in ("EU", "US", "China"):
        game.orders[f].deployments[FRONTS[0]] = 100
    result = resolve_round(game)
    assert result.nations["EU"].deployments[FRONTS[0]] == 100
    assert result.nations["US"].deployments[FRONTS[0]] == 100
    assert result.nations["China"].deployments[FRONTS[0]] == 89
    assert sum(result.fronts[FRONTS[0]].influence.values()) == 0


def test_russian_trait_reduces_opposing_effectiveness():
    game = new_game()
    for f in ("EU", "Russia"):
        game.orders[f].deployments[FRONTS[0]] = 100
    result = resolve_round(game)
    assert result.nations["EU"].deployments[FRONTS[0]] == 99
    assert result.nations["Russia"].deployments[FRONTS[0]] == 99.1


def test_mutual_destruction_has_no_first_mover_advantage():
    game = new_game(rules=Rules(combat_attrition=1, combat_base_decay=1))
    for f in ("EU", "China"):
        game.orders[f].deployments[FRONTS[0]] = 100
    result = resolve_round(game)
    assert result.nations["EU"].deployments[FRONTS[0]] == 0
    assert result.nations["China"].deployments[FRONTS[0]] == 0
    assert result.fronts[FRONTS[0]].status == "Mutual withdrawal"


def test_influence_displaces_rivals_without_exceeding_front_capacity():
    game = new_game()
    game.fronts[FRONTS[0]].influence["China"] = 95
    game.orders["EU"].deployments[FRONTS[0]] = 50
    result = resolve_round(game)
    assert result.fronts[FRONTS[0]].influence["China"] == 90
    assert result.fronts[FRONTS[0]].influence["EU"] == 10
    for _ in range(20):
        result = resolve_round(result)
        invariant(result)
    assert result.fronts[FRONTS[0]].influence["EU"] == pytest.approx(100)


def test_optional_objective_does_not_stop_simulation():
    game = new_game(rules=Rules(victory_mode="influence", victory_target=10))
    game.orders["EU"].deployments[FRONTS[0]] = 10
    result = resolve_round(game)
    assert result.winner == "EU"
    assert resolve_round(result).round == 3


@pytest.mark.parametrize("faction", FACTIONS)
def test_twenty_year_computer_campaigns_remain_valid(faction):
    game = scenario_game(player=faction)
    for _ in range(20):
        game = resolve_round(prepare_ai_orders(game))
        invariant(game)
    assert game.round == 21
    assert loads(dumps(game)) == game


def test_save_roundtrip_preserves_pending_orders_and_identical_next_turn():
    game = resolve_round(prepare_ai_orders(new_game()))
    game.orders["EU"].investments = {"research": 5}
    game.submitted = ["EU"]
    loaded = loads(dumps(game))
    assert loaded == game
    assert resolve_round(prepare_ai_orders(loaded)) == resolve_round(prepare_ai_orders(game))


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(schema_version=99),
    lambda d: d["nations"]["EU"].update(currency=-1),
    lambda d: d["nations"]["EU"].update(content=float("nan")),
    lambda d: d["nations"]["EU"].update(buildings={}),
    lambda d: d["contracts"][0].update(lender=d["contracts"][0]["borrower"]),
    lambda d: d["orders"]["EU"]["deployments"].update({FRONTS[0]: 99999}),
    lambda d: d["fronts"][FRONTS[0]]["influence"].update(EU=101),
    lambda d: d["rules"].update(factory_output=0),
    lambda d: d["nations"]["EU"]["relations"].update(US=1),
])
def test_malformed_saves_rejected(mutate):
    data = new_game().to_dict()
    mutate(data)
    with pytest.raises(ValueError):
        loads(json.dumps(data))


def test_save_size_limit():
    with pytest.raises(ValueError, match="2 MB"):
        loads(" " * 2_000_001)
