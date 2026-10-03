"""The map must distinguish current troops from persistent territorial influence."""

from copy import deepcopy
import xml.etree.ElementTree as ET

import pytest

from ww3.catalog import FACTIONS, FRONTS
from ww3.engine import new_game
from ww3.map_view import render_map


NS = {"svg": "http://www.w3.org/2000/svg"}


def marker(root, front):
    return root.find(f"svg:g[@data-front='{front}']", NS)


def segments(group, metric):
    bar = group.find(f"svg:g[@class='{metric}-bar']", NS)
    return {rect.attrib["data-faction"]: float(rect.attrib["width"])
            for rect in bar.findall("svg:rect[@data-faction]", NS)}


def description(group):
    return group.find("svg:desc", NS).text


def test_map_separates_resolved_troops_influence_and_unclaimed_territory():
    game = new_game()
    # A draft is deliberately different: the map describes the resolved world.
    game.orders["EU"].deployments[FRONTS[0]] = 0
    before = deepcopy(game)
    root = ET.fromstring(render_map(game, FRONTS[0], interactive=True))
    east = marker(root, FRONTS[0])
    assert "Contested" in description(east)
    assert "EU: 60.0 power, 42.9% troop share, 35.0/100 influence" in description(east)
    assert "20.0/100 influence unclaimed" in description(east)
    troops = segments(east, "troop")
    influence = segments(east, "influence")
    assert troops == pytest.approx({"EU": 264 * 60 / 140, "Russia": 264 * 80 / 140}, abs=.001)
    assert influence == pytest.approx({"EU": 264 * .35, "Russia": 264 * .45})
    assert sum(troops.values()) == pytest.approx(264)
    assert sum(influence.values()) == pytest.approx(264 * .8)
    assert game == before


def test_empty_and_tied_troops_do_not_invent_a_faction_leader():
    game = new_game()
    for faction in FACTIONS:
        game.nations[faction].deployments[FRONTS[0]] = 0
    game.fronts[FRONTS[0]].status = "Uncommitted"
    root = ET.fromstring(render_map(game, interactive=True))
    east = marker(root, FRONTS[0])
    assert segments(east, "troop") == {}
    assert "No forces" in " ".join(east.itertext())
    assert "35.0/100 influence" in description(east)
    # A neutral marker is not colored by the first faction or influence leader.
    neutral_color = east.find("svg:circle", NS).attrib["stroke"]
    game.nations["EU"].deployments[FRONTS[0]] = 50
    game.nations["Russia"].deployments[FRONTS[0]] = 50
    game.fronts[FRONTS[0]].status = "Contested"
    tied = marker(ET.fromstring(render_map(game, interactive=True)), FRONTS[0])
    assert segments(tied, "troop") == {"EU": 132, "Russia": 132}
    assert tied.find("svg:circle", NS).attrib["stroke"] == neutral_color


def test_map_keeps_keyboard_selection_contract_and_escapes_status():
    game = new_game()
    game.fronts[FRONTS[0]].status = "EU + US · uncontested <resolved>"
    root = ET.fromstring(render_map(game, FRONTS[2], interactive=True))
    buttons = root.findall("svg:g[@role='button']", NS)
    assert len(buttons) == 4
    assert {button.attrib["data-front"] for button in buttons} == set(FRONTS)
    assert all(button.attrib["tabindex"] == "0" for button in buttons)
    assert all(button.attrib["aria-label"] == f"Select {button.attrib['data-front']} theater" for button in buttons)
    assert all(button.attrib["aria-describedby"] == button.find("svg:desc", NS).attrib["id"] for button in buttons)
    assert [button.attrib["data-front"] for button in buttons if button.attrib["aria-pressed"] == "true"] == [FRONTS[2]]
    assert all(button.find("svg:rect[@class='target']", NS) is not None for button in buttons)
    assert game.fronts[FRONTS[0]].status in description(marker(root, FRONTS[0]))
    assert root.find(".//svg:resolved", NS) is None
    static = ET.fromstring(render_map(game))
    assert static.attrib["role"] == "img"
    assert static.findall(".//*[@tabindex]") == []
