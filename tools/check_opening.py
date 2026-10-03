"""Optional real-browser smoke check. Use a server with a throwaway recovery dir.

Run: WW3_CHROME=/usr/bin/google-chrome python tools/check_opening.py --url http://127.0.0.1:8502
Requires playwright; no browser binaries are installed by the application.
"""

import argparse
import json
import os
from pathlib import Path
import tempfile

from playwright.sync_api import expect, sync_playwright


def metric(page, label):
    return page.get_by_test_id("stMetric").filter(
        has=page.get_by_test_id("stMetricLabel").get_by_text(label, exact=True)).last.get_by_test_id("stMetricValue")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", default=tempfile.mkdtemp(prefix="ww3-browser-"))
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get("WW3_CHROME"), headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 1280, "height": 720}, reduced_motion="reduce")
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(args.url, wait_until="networkidle")
        if page.get_by_role("button", name="Choose faction & mode", exact=True).count():
            page.screenshot(path=str(output / "intro-1280x720.png"))
            page.get_by_role("button", name="Choose faction & mode", exact=True).click()
            page.get_by_role("button", name="Take command", exact=True).wait_for()
        # The caller supplies a disposable server: start a fresh scenario even
        # if a previous invocation left its own checkpoint behind.
        if not page.get_by_role("button", name="Take command", exact=True).count():
            page.get_by_text("New simulation", exact=True).click()
            page.get_by_role("button", name="Return to scenario setup", exact=True).click()
        page.get_by_role("button", name="Take command", exact=True).click()
        for front in ("Eastern Europe", "Pacific & South China Sea", "Arctic", "South America"):
            marker = page.get_by_role("button", name=f"Select {front} theater", exact=True)
            marker.focus()
            page.keyboard.press("Enter")
            expect(page.get_by_role("heading", name=front, exact=True)).to_be_visible()
        page.get_by_role("button", name="Select Eastern Europe theater", exact=True).click()
        expect(page.get_by_role("heading", name="Eastern Europe", exact=True)).to_be_visible()
        page.get_by_text("Objectives", exact=True).first.click()
        expect(page.get_by_role("heading", name="Strategic objectives", exact=True)).to_be_visible()
        expect(page.get_by_text("Expected hold after combat: 0 / 3 years", exact=True)).to_be_visible()
        expect(page.get_by_text("Still contested after combat", exact=False)).to_be_visible()
        page.locator('[data-testid="stMain"]').evaluate("el => el.scrollTo(0, 0)")
        page.screenshot(path=str(output / "objectives-1280x720.png"))
        page.set_viewport_size({"width": 1280, "height": 1400})
        page.screenshot(path=str(output / "objectives-1280x1400.png"))
        page.set_viewport_size({"width": 1280, "height": 720})
        page.get_by_role("button", name="Inspect Eastern Europe", exact=True).first.click()
        expect(page.get_by_role("heading", name="Military fronts", exact=True)).to_be_visible()
        expect(page.get_by_role("heading", name="Eastern Europe", exact=True)).to_be_visible()
        deployed = page.get_by_label("Deploy power → Eastern Europe", exact=True)
        old = float(deployed.input_value())
        deployed.fill("35")
        deployed.press("Tab")
        expect(metric(page, "Your planned front upkeep")).to_have_text("0.175 T")
        page.get_by_role("button", name="Undo edit", exact=True).click()
        expect(metric(page, "Your planned front upkeep")).to_have_text(f"{old * .005:.3f} T")
        page.locator('[data-testid="stMain"]').evaluate("el => el.scrollTo(0, 1100)")
        box = page.locator(".st-key-planning_summary").bounding_box()
        assert 50 <= box["y"] < 100, box
        page.screenshot(path=str(output / "planning-1280x720.png"))
        page.get_by_label("Show opening guidance", exact=True).focus()
        page.keyboard.press("Space")
        expect(page.get_by_label("Show opening guidance", exact=True)).not_to_be_checked()
        page.get_by_text("Economy & construction", exact=True).first.click()
        factory = page.get_by_label("Productivity → Factory", exact=True)
        factory.fill("10")
        factory.press("Tab")
        expect(metric(page, "Productivity")).to_have_text("15.00")
        page.get_by_text("Compare draft alternatives", exact=True).click()
        page.get_by_role("button", name="Remember this draft", exact=True).click()
        research = page.get_by_label("Productivity → Research lab", exact=True)
        research.fill("10")
        research.press("Tab")
        end_year = page.get_by_role("button", name="End year · resolve all factions", exact=True)
        expect(end_year).to_be_disabled()
        page.get_by_role("button", name="Undo edit", exact=True).click()
        expect(end_year).to_be_enabled()
        page.get_by_role("button", name="Reset draft", exact=True).click()
        expect(metric(page, "Productivity")).to_have_text("10.00")
        page.get_by_role("button", name="Restore remembered draft", exact=True).click()
        expect(metric(page, "Productivity")).to_have_text("15.00")
        expected = float(metric(page, "Treasury · T USD").inner_text().replace(",", ""))
        end_year.click()
        expect(page.get_by_text("YEAR 2027 · ROUND 2", exact=True)).to_be_visible()
        page.get_by_role("button", name="Skip review / return to planning", exact=True).click()
        page.get_by_role("button", name="Replay 2026 results", exact=True).click()
        page.get_by_role("button", name="Next phase", exact=True).click()
        expect(page.get_by_text("2/6 · Economy & shortages", exact=True)).to_be_visible()
        page.get_by_role("button", name="Skip review / return to planning", exact=True).click()
        page.reload(wait_until="networkidle")
        expect(page.get_by_text("YEAR 2027 · ROUND 2", exact=True)).to_be_visible()
        expect(page.get_by_label("Show opening guidance", exact=True)).not_to_be_checked()
        page.get_by_text("Sound & display", exact=True).click()
        page.evaluate("""() => {
            window.soundNotes = [];
            const original = OscillatorNode.prototype.start;
            OscillatorNode.prototype.start = function(...args) {
                window.soundNotes.push(this.frequency.value);
                return original.apply(this, args);
            };
        }""")
        page.get_by_label("Sound effects", exact=True).focus()
        page.keyboard.press("Space")
        expect(page.get_by_role("button", name="Test sound", exact=True)).to_be_enabled()
        page.get_by_role("button", name="Test sound", exact=True).click()
        expect(page.get_by_text("Sound ready.", exact=True)).to_be_visible()
        page.wait_for_function("window.soundNotes.length >= 3")
        assert page.evaluate("window.soundNotes.slice(-3)") == [330, 440, 660]
        count = page.evaluate("window.soundNotes.length")
        page.get_by_text("Situation room", exact=True).first.click()
        expect(page.get_by_role("heading", name="Situation room", exact=True)).to_be_visible()
        assert page.evaluate("window.soundNotes.length") == count
        page.get_by_label("Sound effects", exact=True).focus()
        page.keyboard.press("Space")
        expect(page.get_by_role("button", name="Test sound", exact=True)).to_be_disabled()
        page.get_by_role("group", name="Text size", exact=True).get_by_role("slider").focus()
        page.keyboard.press("End")
        page.wait_for_function("getComputedStyle(document.documentElement).fontSize === '24px'")
        page.locator('[data-testid="stMain"]').evaluate("el => el.scrollTo(0, 0)")
        assert page.locator('[data-testid="stMain"]').evaluate("e => e.scrollWidth <= e.clientWidth + 1")
        assert page.get_by_role("button", name="Undo edit", exact=True).locator("p").evaluate("e => e.scrollWidth <= e.clientWidth + 1")
        page.screenshot(path=str(output / "large-text-150.png"))
        page.reload(wait_until="networkidle")
        page.wait_for_function("getComputedStyle(document.documentElement).fontSize === '24px'")
        page.get_by_text("Sound & display", exact=True).click()
        page.get_by_role("group", name="Text size", exact=True).get_by_role("slider").focus()
        page.keyboard.press("Home")
        page.wait_for_function("getComputedStyle(document.documentElement).fontSize === '16px'")
        page.get_by_text("Save / load game", exact=True).click()
        with page.expect_download() as download:
            page.get_by_role("button", name="Download save", exact=True).click()
        save = output / "campaign.json"
        download.value.save_as(save)
        game = json.loads(save.read_text())
        assert game["schema_version"] == 3
        assert abs(game["nations"]["EU"]["currency"] - expected) < .0051
        page.locator('input[type="file"]').set_input_files(save)
        page.get_by_role("button", name="Load selected save", exact=True).click()
        expect(page.get_by_text("YEAR 2027 · ROUND 2", exact=True)).to_be_visible()
        page.get_by_text("Situation room", exact=True).first.click()
        for width, height in ((1920, 1080), (390, 844)):
            page.set_viewport_size({"width": width, "height": height})
            page.locator('[data-testid="stMain"]').evaluate("el => el.scrollTo(0, 0)")
            if width < 900:
                collapse = page.get_by_test_id("stSidebarCollapseButton").locator("button")
                if page.get_by_test_id("stSidebar").get_attribute("aria-expanded") == "true":
                    collapse.focus()
                    page.keyboard.press("Enter")
                expect(page.get_by_test_id("stSidebar")).to_have_attribute("aria-expanded", "false")
                page.wait_for_function("document.querySelector('[data-testid=stSidebar]').getBoundingClientRect().right <= 1")
            assert page.locator('[data-testid="stMain"]').evaluate("e => e.scrollWidth <= e.clientWidth + 1")
            page.screenshot(path=str(output / f"command-{width}x{height}.png"), animations="disabled")
            map_region = page.get_by_role("region", name="Strategic world map; scroll horizontally on narrow screens", exact=True)
            map_region.screenshot(path=str(output / f"map-{width}x{height}.png"), animations="disabled")
            if width < 900:
                assert map_region.evaluate("e => e.scrollWidth > e.clientWidth")
                assert map_region.evaluate("""e => {
                    const card = e.querySelector('[data-front][aria-pressed="true"] .target').getBoundingClientRect();
                    const viewport = e.getBoundingClientRect();
                    return card.left >= viewport.left - 1 && card.right <= viewport.right + 1;
                }""")
                marker = page.get_by_role("button", name="Select Arctic theater", exact=True)
                marker.focus()
                page.keyboard.press("Enter")
                expect(page.get_by_role("heading", name="Arctic", exact=True)).to_be_visible()
                assert page.locator('[data-testid="stMain"]').evaluate("e => e.scrollWidth <= e.clientWidth + 1")
        assert not page.get_by_test_id("stException").count()
        assert not errors, errors
        print(json.dumps({"keyboard_theaters": 4, "sticky_summary": True, "undo": True,
            "objective_forecast_and_theater_navigation": True, "mobile_map_pan_and_keyboard": True,
            "selected_map_card_visible_after_resize": True,
            "invalid_draft_blocked": True, "review_skip_replay": True, "reload": True,
            "draft_comparison_restore": True, "audio_test_and_mute": True, "text_scale_reload": True,
            "manual_save_import": True, "forecast_currency": expected,
            "resolved_currency": game["nations"]["EU"]["currency"], "browser_errors": errors,
            "screenshots": str(output)}, indent=2))
        browser.close()


if __name__ == "__main__":
    main()
