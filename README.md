# Geopolitics / WW3

A playable local strategy prototype for the EU, US, China, and Russia. Play one faction against computer opponents, four-player hotseat, or a sandbox controlling every faction. Plan an economy, negotiate agreements, and contest four fronts while seeing the expected resource consequences of your orders.

## Documentation

| Document | Authority and purpose |
|---|---|
| [DESIGN.md](DESIGN.md) | Single source of truth for current gameplay: formulas, initial assets, objectives, agreed decisions, and configurable defaults. |
| [NEXT_STEPS.md](NEXT_STEPS.md) | Prioritized development and Steam release roadmap, with proposed work, acceptance criteria, risks, and decisions still to make. |
| [README.md](README.md) | Current implementation status, installation, testing, and project navigation. |
| [PLAYTEST_REPORT.md](PLAYTEST_REPORT.md) | Latest improvements, 16 objective-driven campaigns, balance findings, and prioritized follow-up experiments. |

The superseded design inputs have been removed. Roadmap proposals become gameplay rules only when incorporated into `DESIGN.md` and implemented with corresponding validation.

## Current status — 4 October 2026

The local prototype implements the reconciled rules, including simultaneous annual turns, construction and supply chains, diplomacy, debt contracts, persistent forces, coalition combat, recoverable influence, and faction objectives. The opening scenario is contested; the default victory requires three consecutive resolved years. Live forecasts use the actual resolution rules and update as orders change. Portable saves preserve plans and scenario settings.

The implementation passes **227 automated Python tests**, including exact construction/theater/objective forecasts, partial and paused construction workflows, victory warnings, map data, draft comparison/undo, phase reports, recovery failures, presentation preferences, scenario validation, strategic campaign replay, and hotseat relaunches. Two Godot integration suites exercise the actual desktop scene and Python worker. These checks establish a functional baseline; broader campaign balance, player retention, accessibility, and commercial demand still need evaluation.

Both clients provide campaign setup, all gameplay orders, forecasts, objectives, history, draft comparison, undo/reset, first-three-year guidance, turn reviews, recovery, and sound/display preferences. The Python simulation remains authoritative. Streamlit stays available as the development/debugging client; Godot now covers its gameplay workflows with native desktop controls. The desktop presentation is functional, and its visual direction and original game graphics are the next work. Production packaging, Steam integration, and player-validated onboarding remain future work. Turn review uses instant manual steps without animation. See the active polish and graphic generation plan in [NEXT_STEPS.md, section 11](NEXT_STEPS.md#11-visual-polish-and-graphic-generation).

The commercial ambition is a Steam top-10 launch. [NEXT_STEPS.md](NEXT_STEPS.md) defines a provisional chart target and the evidence needed to justify further investment. The immediate work is to establish an art direction for the Godot client, generate original game graphics, and polish the command screens around the existing mechanics and resource forecasts.

The latest improvement pass adds separate troop-share and influence bars to every map theater, readable horizontal map panning on narrow screens, and an Objectives dashboard with current-versus-post-combat values, precise gaps, coalition blockers, theater shortcuts, and a four-faction victory watch. Commit-area alerts expose shortages, operating deficits, borrowing, hold resets, and expiring productivity. The [playtest report](PLAYTEST_REPORT.md) records 12 objective-driven wins and four unresolved Russian campaigns; the standard opponents and numerical rules remain unchanged.

## Godot desktop client

Install the Python simulation and open `clients/godot/project.godot` with **Godot 4.5+ (standard edition)**. Godot 4.5.1 has been used for verification. From this repository:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python tools/run_godot.py --godot /path/to/Godot
```

If `godot` or `godot4` is on PATH, omit `--godot`. On Windows use `.venv\Scripts\python.exe` for the Python commands. Running from the Godot editor discovers the repository's `.venv`; set `WW3_PYTHON` to an absolute interpreter path for a different environment.

The eight command screens cover the existing game's features:

| Screen | Available controls and information |
|---|---|
| Situation | Four selectable fronts, separate troop-share/influence bars, current and forecast coalitions, faction statistics, infrastructure, briefing and opening guidance. |
| Economy | All eight facilities and four projects, startup costs, productivity allocations, partial/paused work, completions, production and upkeep. |
| Diplomacy | Tariffs, matching trade/alliance offers, US/China benefit sharing, outreach, foreign aid, relationships and active agreements. |
| Military | All deployments, reserve, capacity/recovery, dominance bonuses, planned forces, survivors, upkeep, influence and affected objectives. |
| Government | Taxes, government transitions, domestic repayment, foreign principal repayment and lender renewal rates at maturity. |
| Objectives | Any faction's current/expected conditions, gaps, blockers, advice, theater shortcuts, hold progress and victory watch. |
| Chronicle | Nine history metrics with four-faction charts and exact values; every retained annual report. |
| Rules | Selectable/exportable `DESIGN.md` and the current scenario settings. |

The header keeps resource balances and draft actions visible. **Ledger & alternatives** provides the complete forecast breakdown, cash flows, shortages, changed decisions, and remembered-plan comparisons. **New campaign** exposes solo/hotseat/sandbox, all factions, all three victory modes, balance settings, AI seed and starting resources. Hotseat includes submission locks, reopening and a saved handoff. Results open a skippable six-phase review with links from headlines to their causes. Victories allow continued play.

**Settings** provides opt-in synthesized sound, volume, 100–150% text sizes, reduced motion and optional opening guidance. Preferences, selected page/front, commander and review position are saved with local recovery, separately from portable game data. All turn review steps are instant. Undo and remembered alternatives last for the current year and worker session, matching Streamlit. This is a repository-based development client; a distributable bundled Python runtime, a C# port, and Steam integration are not implemented yet.

The client launches one local Python worker using pipes, with IO on a separate thread. No web server or internet connection is used during play. The client stops its worker when it closes. Godot saves to `user://recovery` under its `ww3-godot` user-data directory; `WW3_GODOT_SAVE_DIR` can select a disposable directory. These saves are separate from Streamlit. Export/import portable JSON to move a campaign between clients, and run only one client instance per recovery directory.

## Streamlit development client

Requires Python 3.10 or newer. From this directory:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run clients/streamlit/app.py
```

The original `streamlit run app.py` command remains a compatibility launcher.

Open **http://localhost:8501**. The default server listens only on this computer. No accounts, API keys, external map services, or internet connection are required after installation.

The opening screen presents **Power has a price**, a world briefing over original generated military-industrial artwork. Its narrative connects energy, minerals, compute, productivity, treasury/debt, and the four factions' objectives. Text remains selectable and readable at larger sizes; the artwork is bundled locally for offline use. The [generation prompt and provenance](assets/intro-art.json) accompany the [background](assets/intro-war-room.png).

Use **Start EU campaign** on the introduction, or **Choose faction & mode** to configure the scenario and select **Take command**. An existing local checkpoint resumes directly; use **View opening briefing** in the sidebar to revisit the intro, then **Continue campaign** to return to the same page, orders, and game year. The introduction also accepts portable saves. In the situation room or military screen, select any theater on the map (click or Tab + Enter/Space) or use **Inspect theater**. Edit deployments to compare planned coalitions, military shares, upkeep, expected survivors, territorial influence, and relevant objectives. The map itself depicts the resolved world. Solo predictions include the same computer response used at resolution; shared-player predictions remain conditional on other drafts.

The planning ledger stays above every command screen and remains visible while scrolling on desktop. It separates current resources, orders/transfers, annual changes, and expected balances. On narrow screens it scrolls with the page so controls remain reachable. **Undo edit** restores the previous edit for this faction; **Reset draft** restores standing orders and can itself be undone. Up to 50 edits per faction are retained within the current year/session. Committed hotseat drafts stay locked until reopened. Invalid drafts clear projected values instead of showing stale forecasts.

In **Economy & construction**, the **Construction status** table and each investment card separate completed facilities, saved progress, this year's productivity allocation, expected completions, and work left for later. Assigning productivity only drafts an order: construction happens at **End year**. Completed facilities produce and pay upkeep in that same update, with remaining output available for your next orders. Unfinished work produces nothing and needs a new allocation in a later year; allocations do not repeat automatically. For example, put 5 productivity into a factory and end the year to save 50% progress. Assign another 5 next year to finish it, or leave it paused. Full resource costs are charged when each unit starts, including partially built units; continuing that unit does not charge startup costs again. The preview includes trade discounts and clears when any draft is invalid. Last year's completions stay visible above the table.

Open **Compare draft alternatives** to remember a plan, edit another, and compare their expected resources, military shares, influence and objective hold. Both alternatives are recalculated against the current world and rival drafts. **Restore remembered draft** is undoable. One alternative per faction lasts for the current year and open session; exporting or reloading retains the active draft, not the remembered alternative.

**Sound & display** in the sidebar provides optional original synthesized cues, a test button, volume from 0–100%, text sizes from 100–150%, and reduced motion. Sound starts muted and needs a browser interaction to activate. Audio events accompany applied edits, commitments, invalid drafts and results; navigation does not replay them. All information remains available visually. Preferences recover with the local campaign and remain separate from portable gameplay saves. At larger text sizes the planning ledger scrolls with the page and its buttons use a separate row.

Opening guidance in the sidebar suggests investments, diplomacy, deployments, forecasts and objective checks for the first three years. It can be skipped, allows alternative choices, and describes actual orders/results. **End year** commits all orders. The result review follows treaties/orders → economy/shortages → relations → combat/influence → society → objectives. Three ranked headlines link to their recorded phase; skip, advance manually or replay without advancing time. There is no scripted victory or changed hold requirement.

Applied edits and resolved turns are automatically saved to **`.saves/streamlit/current.json`**, with the previous validated checkpoint in **`.saves/streamlit/previous.json`**. Refreshing, reopening the app, or restarting its server resumes the campaign, drafts (including overallocated drafts), hotseat handoff, and guidance preference. Press Enter or leave a number field to apply its edit before closing. A partial replacement cannot overwrite the last valid checkpoint; damaged current files fall back to the previous copy. **Save / load game** also offers explicit latest/previous recovery and portable downloads/imports. If both checkpoints are damaged, import a manual save or start a new campaign. Disk errors are displayed and manual export remains available.

On first launch after migration, an existing legacy `.saves/current.json` (or valid previous checkpoint) is copied into the new Streamlit slot, leaving the original files intact. An explicit `WW3_SAVE_DIR` keeps its existing meaning and disables this automatic migration.

Recovery is one local slot per server installation, not a browser account. A stale tab cannot overwrite a newer checkpoint: download its draft or reload the latest checkpoint when warned. Starting a new campaign uses this same slot; download campaigns you want to keep separately. For isolated runs, set `WW3_SAVE_DIR` to another writable directory. Run only one server per recovery directory. Undo history is session-only; the draft itself is durable.

Portable saves use validated JSON, now **schema version 3**, with a separate **gameplay rules version `1`**. No gameplay coefficients or AI policies changed in this slice. Version 2 saves retain their assets, drafts and original reports; new turns add structured phase boundaries/headlines. Version 1 prototype saves can still be imported: assets/history are retained, military capacity is inferred from current/initial strength, objective streaks begin at zero, tariffs are capped at 50%, and subsequent turns use the reconciled mechanics. Unknown rules versions are rejected. Save files remain limited to 2 MB; a verified 100-year campaign was about 1.28 MB.

## Tests

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

Tests cover economic accounting, construction, shortages, military coalitions, objective thresholds and consecutive-year progress, deterministic forecasts, JSON persistence, computer campaigns, and Streamlit interface workflows. UI tests use Streamlit AppTest and do not require a browser installation. Application tests verify shared session commands and the original-engine fixture in `tests/fixtures/migration-baseline.json`; bridge tests exercise revision conflicts, duplicate commands, malformed requests, persistence failures, and actual subprocess framing.

For simulation-only development, install `.[test]` and run the suites independently of Streamlit:

```bash
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m pytest tests/core tests/application tests/persistence tests/bridge -q
```

Run the real Godot scene and worker through both headless integration suites:

```bash
.venv/bin/python tools/run_godot.py --godot /path/to/Godot --smoke
```

The launcher allocates temporary recovery storage. `smoke.gd` checks map selection, full-precision edits, forecast/result equality, partial construction, portable saves, restart recovery, invalid drafts, hotseat locks/reopening and worker shutdown. `features.gd` uses the native controls for all investments, diplomacy, government transitions, debt maturity, scenarios, comparisons, reviews, history, preferences and continued play after a recorded victory. It also verifies that presentation changes never alter portable game saves.

The feature suite can run with a real display by omitting `--headless` and setting disposable `WW3_GODOT_SAVE_DIR` and `WW3_GODOT_CAPTURE_DIR` paths; use `--script res://tests/features.gd` with `--path clients/godot`. It captures all command screens, planning/review dialogs and large-text rendering. The feature suite was also checked with Godot 4.5.1 on a virtual X11 display. This does not replace platform packaging or player accessibility checks.

For an optional real-browser check, install `playwright` in the environment and a Chromium browser (`python -m playwright install chromium`, or set `WW3_CHROME` to an installed Chrome executable). Start an **isolated test server**—the browser check starts a fresh scenario in its recovery slot:

```bash
WW3_SAVE_DIR=/tmp/ww3-browser-test .venv/bin/python -m streamlit run app.py --server.port 8502
# In another terminal:
.venv/bin/python tools/check_opening.py --url http://127.0.0.1:8502
```

The check exercises all map markers with the keyboard, deployment edits, undo, draft comparison, invalid drafts, forecast/result equality, sound/mute, text scaling and preference recovery, review skip/replay, refresh, export/import and desktop/narrow layouts. Screenshots and a portable campaign are written to a temporary directory printed at completion.

To repeat the three authored five-year UI campaigns on the same disposable server, run:

```bash
.venv/bin/python tools/play_campaigns.py --url http://127.0.0.1:8502
```

This plays EU, China and Russia with different investments, diplomacy and deployments, checks 75 displayed resource forecasts, reloads each campaign, and retains yearly draft/result saves. It is scripted agent play, not evidence from new human players. Run the browser tools sequentially because they share the server's recovery slot.

The [recorded playthroughs](playtests/browser-playthroughs-2026-10-03.json) completed all 15 years: 75 forecasts matched, all three reloads passed, and every downloaded result save matched a complete engine replay. Replays are retained under `playtests/replays/browser-{EU,China,Russia}-17`; use the replay command below with one of those directories. These short varied openings did not reach an objective hold. Captures of the [introduction](playtests/captures/intro-1280x720.png), [large text](playtests/captures/large-text-150.png), and [narrow layout](playtests/captures/command-390x844.png) document the current presentation.

## Campaign diagnostics

The evaluation runner compares the current computer policy with factory expansion, military concentration, research and cooperation. Each selected faction faces the existing computer opponents. The `current` policy controls all four factions with the existing AI, so faction labels for a given seed repeat the same world trajectory and are not independent samples.

```bash
# Output must be a new directory; existing experiments are never overwritten.
.venv/bin/python -m ww3.evaluation run --output /tmp/ww3-campaigns --seeds 17 23 41 --turns 30
.venv/bin/python -m ww3.evaluation replay /tmp/ww3-campaigns/EU-military-17
```

Optional `--factions EU China` and `--policies factory military` select a smaller experiment. Every case writes an initial save, recorded orders with per-year state hashes/metrics, a final save, and a summary; the runner replays every case before reporting success. It stops at first victory or the observation limit. That limit is an experimental window, not a game turn cap or a draw. Replays use the recorded orders rather than replanning the AI.

The [3 October baseline](playtests/campaign-baseline-2026-10-03.json) completed and replayed **60 configurations**: four factions × five policies × three seeds, observed for up to 30 years. **54 remained unresolved; six ended in Chinese victories in years 26–27, with no tested policy winning its own campaign.** Factory policies grew much faster but did not secure victory. These simple policies expose a potential objective/strategy stalemate; they do not prove that human campaigns are unwinnable or identify a balanced standard opponent. M2 should investigate objective pursuit and denial before changing coefficients. A [retained campaign](playtests/replays/EU-military-17/summary.json) can be replayed with `python -m ww3.evaluation replay playtests/replays/EU-military-17`.

The subsequent [objective campaign matrix](playtests/objective-campaigns-2026-10-03/results.json) covers **16 campaigns and 360 resolved years**: all four factions × two deterministic objective policies × seeds 17/23, up to 45 years. EU, US, and China each won all four cases; Russia remained unresolved in all four. All cases retain replayable orders and saves. The policies use public forecasts, supply planning, diplomacy, and complete-objective deployment decisions. They are experimental players, not replacement AI. See [PLAYTEST_REPORT.md](PLAYTEST_REPORT.md) for the strategy tradeoffs and limitations.

```bash
.venv/bin/python -m ww3.evaluation run --output /tmp/ww3-objectives --policies objective objective-industry --seeds 17 23 --turns 45
.venv/bin/python -m ww3.evaluation replay playtests/objective-campaigns-2026-10-03/EU-objective-17
.venv/bin/python -m tools.probe_balance
```

[Improvement verification](playtests/improvement-evidence-2026-10-03.json) records the latest test/browser results, source hashes, and objective-campaign archive. The earlier [opening-slice evidence](playtests/implementation-evidence.json) records its build fingerprint, campaign diagnostics and authored playthroughs; the [2 October evidence](playtests/implementation-evidence-2026-10-02.json) retains the long-save check and backend timing samples. These measurements do not establish the roadmap's player or minimum-hardware gates.

## Opening playtests still needed

Use [playtests/observations.csv](playtests/observations.csv) for N01's first 10 fresh players and N07's separate 30-player repeat. There are **no participant results yet**. Record the build, seed, faction, recruiting source, prior experience, first action, time to a valid plan and first resolved year, confusion, voluntary continuation and stopping reason. Save reproducible campaigns/openings across all four factions. Identifiers and recordings are optional; do not collect recordings without consent.

After the first resolution, ask the player to explain one resource change and the difference between military share and territorial influence. Score forecast understanding correct only when they connect an actual order/annual flow to its balance; score share/influence correct only when they distinguish current troop proportions from persistent territorial control. After a later turn, ask for the main gain/loss and its cause without explaining the answer first. Record the player's words before scoring. Include early exits in the denominator, exclude idle time, and observe actual replay/return separately from stated interest. These observations, not automated victories, determine the roadmap's player gates.

## Project structure

One repository contains an independently installable Python simulation and two clients:

```text
src/ww3/
  core/                 Models, rules, AI, forecasts, economic/combat resolution
  application/          GameSession, draft history, briefings, command read model
  persistence/          Portable saves, migrations, atomic recovery, preferences
  bridge/               Local JSON worker and process entry point
  evaluation.py         Campaign diagnostics and deterministic replay
  objective_policy.py   Experimental players for balance evaluation
clients/
  streamlit/            Complete development client (package: ww3_streamlit)
  godot/                Native command screens, scenario dialog, charts, client tests
contracts/              Protocol 1 JSON schemas and example requests
tests/                 Core, application, persistence, bridge, Streamlit suites
  fixtures/             Legacy save and frozen pre-migration campaign results
tools/                  Launchers, browser campaigns, balance probes
playtests/              Retained experiment evidence
assets/                 Original Streamlit intro art and provenance
pyproject.toml          Python package and optional dependency groups
app.py                  Compatibility launcher for the Streamlit client
```

`GameSession` owns drafts, undo/alternatives, submission locks, AI preparation, and turn advancement. Clients receive detached snapshots and submit edits explicitly. Forecast and resolution continue to use the same core rules. The core imports neither Streamlit nor pandas; the `streamlit` optional dependency group is only needed for the development client. The Streamlit client uses repository documentation and artwork, so run it from this checkout with the editable install.

```text
Streamlit ────────────────→ GameSession → simulation core
Godot → local JSON worker → GameSession → saves/recovery
```

The worker runs with `python -m ww3.bridge --save-dir <directory>`. Requests and responses are one UTF-8 JSON object per line; stdout is exclusively protocol output. See [request schema](contracts/request-v1.schema.json), [response schema](contracts/response-v1.schema.json), and [example conversation](contracts/examples-v1.jsonl). Protocol version **1**, gameplay rules version **1**, and save schema **3** are independent identifiers.

Each request has a string `id`, `command`, and optional `params`. Mutating commands require `expected_revision`; successful mutations advance the session revision (unchanged edits/empty undo do not). A bounded cache returns the original response for an identical retry; a reused ID with different content is rejected. Revisions and retry IDs are scoped to one worker lifetime. After a restart, read the recovered state and issue fresh commands; clients never automatically replay an uncertain turn.

`edit` patches top-level order fields; a dictionary value replaces that whole map. An oversubscribed draft remains recoverable but has `forecast: null` and a `forecast_error`; invalid structure is rejected. A successful command with failed autosave returns the updated game and `checkpoint_error`, allowing manual export without repeating the command. `export` returns an opaque JSON save string, and `load` accepts that string, preserving numeric types, field ordering, and precision across clients. A request is limited to 4,100,000 bytes, including its newline; an oversized request receives an error and closes the worker. Portable saves retain their 2 MB limit.

State replies also contain `catalog` (facilities, government effects, scenario-control definitions), `desk` (read-only costs, construction, objective briefings, alerts and recorded review phases), and `ui`. The application layer derives these from the same simulation helpers used by Streamlit. `new.params.rules` accepts the scenario fields in the request schema; invalid settings leave the current campaign intact. The optional legacy `seed` parameter remains supported. `ui` requires `expected_revision`, validates presentation/navigation values, and checkpoints them without advancing the gameplay revision or changing portable saves. The Godot client sends UI updates when the worker is idle; it never replays an uncertain game command.

A future C# engine must pass the fixed state/order/forecast/result fixtures and retained campaign replays before replacing Python. Once switched, ongoing developer tools should use the production engine; the old implementation becomes a frozen comparison reference.

Scenario settings exposed in the start screen apply to new games. Other defaults are centralized in `src/ww3/core/rules.py`. Update `DESIGN.md` whenever gameplay rules change, and update `NEXT_STEPS.md` as work meets its acceptance criteria. Keep development dependencies and run commands in this README; keep the design independent of implementation technology.
