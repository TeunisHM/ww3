"""Agent-authored five-year browser playthroughs on an isolated local server.

These are scripted decisions through the actual interface, not human playtests.
Each year retains a portable save and checks its five displayed resource forecasts.
"""

import argparse
import json
import os
from pathlib import Path
import re
import tempfile

from playwright.sync_api import expect, sync_playwright

from check_opening import metric

FACTIONS = ["EU", "US", "China", "Russia"]
FRONTS = ["Eastern Europe", "Pacific & South China Sea", "Arctic", "South America"]
BUILDS = {
    "EU": ["Factory", "Public services", "Research lab", "Drone facility", "Renewable facility"],
    "China": ["Data center", "Research lab", "Factory", "Research program", "Drone facility"],
    "Russia": ["Drone facility", "Factory", "Public services", "Renewable facility", "Military modernization"],
}


def download_game(page, destination):
    expect(page.get_by_test_id("stApp")).to_have_attribute("data-test-script-state", "notRunning", timeout=15000)
    assert not page.get_by_text("Automatic recovery could not save:", exact=False).count()
    button = page.get_by_role("button", name="Download save", exact=True)
    if not button.is_visible():
        page.get_by_text("Save / load game", exact=True).click()
    with page.expect_download() as event:
        button.click()
    event.value.save_as(destination)
    return json.loads(destination.read_text())


def start_campaign(page, faction):
    intro = page.get_by_role("button", name="Choose faction & mode", exact=True)
    if intro.count():
        intro.click()
        page.get_by_role("button", name="Take command", exact=True).wait_for()
    elif not page.get_by_role("button", name="Take command", exact=True).count():
        page.get_by_text("New simulation", exact=True).click()
        page.get_by_role("button", name="Return to scenario setup", exact=True).click()
        page.get_by_role("button", name="Take command", exact=True).wait_for()
    page.get_by_role("combobox", name="Your starting faction", exact=True).click()
    page.get_by_role("option", name=re.compile(rf"^{faction} ·")).click()
    page.get_by_role("button", name="Take command", exact=True).click()
    expect(page.get_by_text("YEAR 2026 · ROUND 1", exact=True)).to_be_visible()


def deploy(page, front, power):
    inputs = {name: page.get_by_label(f"Deploy power → {name}", exact=True) for name in FRONTS}
    old = {name: float(widget.input_value()) for name, widget in inputs.items()}
    if old[front] == power:
        return
    inputs[front].fill(str(power))
    inputs[front].press("Tab")
    total = sum(old.values()) - old[front] + power
    # Wait for the server's computed feedback before editing the next field;
    # otherwise a pending browser rerender can replace the input being typed.
    expect(page.get_by_text(re.compile(rf"^Productivity: .* · Military committed: {total:.1f} /"))).to_be_visible()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, default=Path(tempfile.mkdtemp(prefix="ww3-playthroughs-")))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    findings = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get("WW3_CHROME"), headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(args.url, wait_until="networkidle")
        for faction, projects in BUILDS.items():
            start_campaign(page, faction)
            folder = args.output / faction
            folder.mkdir(exist_ok=True)
            current = download_game(page, folder / "opening.json")
            years = []
            for year, building in enumerate(projects, start=1):
                page.get_by_text("Economy & construction", exact=True).first.click()
                expect(page.get_by_role("heading", name="Economy & construction", exact=True)).to_be_visible()
                points = min(10, current["nations"][faction]["productivity"])
                widget = page.get_by_label(f"Productivity → {building}", exact=True)
                widget.fill(str(points))
                widget.press("Tab")
                expect(page.get_by_text(f"{points:.1f} / {current['nations'][faction]['productivity']:.1f} productivity allocated", exact=True)).to_be_visible()
                if year == 1:
                    page.get_by_text("Diplomacy", exact=True).first.click()
                    target = {"EU": "US", "China": "Russia", "Russia": "China"}[faction]
                    peers = [f for f in FACTIONS if f != faction]
                    offer = page.get_by_label("Offer / maintain trade", exact=True).nth(peers.index(target))
                    if not offer.is_checked():
                        offer.focus()
                        page.keyboard.press("Space")
                        expect(offer).to_be_checked()
                page.get_by_text("Military fronts", exact=True).first.click()
                expect(page.get_by_role("heading", name="Military fronts", exact=True)).to_be_visible()
                # Clear allocations first so the temporary draft never needs
                # more power than exists while moving troops between fronts.
                for front in FRONTS:
                    deploy(page, front, 0)
                budget = int(current["nations"][faction]["military"] * .8)
                primary = FRONTS[1] if faction == "China" else FRONTS[0]
                distribution = {primary: int(budget * .6), FRONTS[2]: budget - int(budget * .6)}
                for front, power in distribution.items():
                    deploy(page, front, power)
                end = page.get_by_role("button", name="End year · resolve all factions", exact=True)
                expect(end).to_be_enabled()
                # Download also waits for the draft rerun and records the exact
                # orders used, allowing later inspection of every play decision.
                draft = download_game(page, folder / f"year-{year}-draft.json")
                assert draft["orders"][faction]["deployments"] == {front: distribution.get(front, 0) for front in FRONTS}
                assert sum(draft["orders"][faction]["investments"].values()) == points
                labels = {"currency": "Treasury · T USD", "energy": "Energy · PJ", "minerals": "Minerals · t", "compute": "Available compute", "productivity": "Productivity"}
                expected = {field: float(metric(page, label).inner_text().replace(",", "")) for field, label in labels.items()}
                end.click()
                expect(page.get_by_text(f"YEAR {2026 + year} · ROUND {year + 1}", exact=True)).to_be_visible()
                page.get_by_role("button", name="Skip review / return to planning", exact=True).click()
                current = download_game(page, folder / f"year-{year}.json")
                assert current["round"] == year + 1
                for field, projected in expected.items():
                    assert abs(current["nations"][faction][field] - projected) <= .0051, (faction, year, field)
                years.append({"resolved_year": year, "investment": building, "productivity_allocated": points,
                    "orders": draft["orders"][faction], "forecast": expected,
                    "actual": {field: current["nations"][faction][field] for field in expected},
                    "objective_streak": current["objective_streaks"][faction], "winners": current["winners"]})
                if year == 3:
                    page.reload(wait_until="networkidle")
                    expect(page.get_by_text(f"YEAR {2026 + year} · ROUND {year + 1}", exact=True)).to_be_visible()
                assert not page.get_by_test_id("stException").count()
            page.get_by_text("Objectives", exact=True).first.click()
            expect(page.get_by_role("heading", name="Strategic objectives", exact=True)).to_be_visible()
            page.screenshot(path=str(folder / "objectives-after-five-years.png"))
            findings.append({"faction": faction, "years": years, "recovered_after_year": 3,
                "final_content": current["nations"][faction]["content"], "final_debt": current["nations"][faction]["domestic_debt"]})
            print(f"{faction}: five years played through UI, forecasts matched, reload passed", flush=True)
        assert not errors, errors
        report = {"kind": "Agent-authored browser playthroughs; not fresh-player evidence", "campaigns": findings,
            "javascript_errors": errors, "resource_forecasts_checked": 75, "human_participants": 0}
        (args.output / "playthroughs.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"campaigns": len(findings), "years_played": 15, "forecasts_checked": 75, "errors": errors, "output": str(args.output)}, indent=2))
        browser.close()


if __name__ == "__main__":
    main()
