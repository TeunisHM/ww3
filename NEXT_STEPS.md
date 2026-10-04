# Geopolitics / WW3 — Next steps toward a Steam release

Updated **4 October 2026**. This is the development roadmap. [DESIGN.md](DESIGN.md) remains the authority for gameplay; [README.md](README.md) describes the runnable prototype. Items below are proposed work unless explicitly marked complete. No Steam listing, audience measurement, or release readiness is established by this document.

## 1. Define the ambition and the product

**Ambition:** create a strategy game capable of reaching Steam's top 10. For planning, interpret this provisionally as reaching rank 10 or better on the **global, unfiltered, real-time Top Sellers chart during the first seven days of the paid release**. Record the chart, timestamp, peak rank, and duration; track the weekly chart separately. Confirm this interpretation before setting a commercial launch target. A regional or genre ranking is a separate result.

Steam's Top Sellers lists use revenue, including purchases, DLC, and in-game transactions. Global and country charts differ. Valve describes the real-time chart as trailing 24-hour spending with extra weight on the most recent three hours. A fixed wishlist count or unit target therefore cannot guarantee a rank. [Steamworks: Top Sellers Lists](https://partner.steamgames.com/doc/store/top_sellers)

The rank is an ambition, not a delivery acceptance criterion. The plan must also support a game worth buying and maintaining if it never reaches that chart position. Set a sustainable sales target once development cost, price, and measured demand are known.

### Proposed positioning

**Player promise:** lead a modern superpower, see the cost of every move, and hold an advantage while rival powers contest it.

The distinctive hook is the connection between economic planning and geopolitical consequences: changing production, debt, treaties, or deployments immediately updates a trustworthy forecast. The simultaneous annual resolution turns those choices into a new strategic situation. The three-year objective hold creates a visible struggle to secure and defend a position.

Primary audience hypothesis: players who enjoy turn-based strategy, political simulations, and board-game-style competition, and value understanding why a plan succeeded or failed. Test that audience before broadening the pitch.

Provisional commercial scope: a premium, offline-capable PC game; Windows first; solo as the main experience, with the existing hotseat and sandbox modes retained. A 20–30-minute introduction is a usability target to test. Full campaign length, additional platforms, final name, price, and release model remain decisions for later evidence. There is no new turn limit or shortened victory rule in this proposal.

### Design references to study

These are references for focused research, not evidence of our likely sales or permission to copy their content. The lessons are our hypotheses, to be checked through hands-on comparison.

| Reference | Relevant premise | Question for our game |
|---|---|---|
| [Terra Invicta](https://store.steampowered.com/app/1176470/Terra_Invicta/) | Rival factions compete for control of Earth and expand into space. | Can our four-front map communicate geopolitical stakes immediately within a much smaller scope? |
| [Democracy 4](https://store.steampowered.com/app/1410710/Democracy_4/) | Policy choices affect a simulated society and the government's survival. | Can a player trace an economic consequence back to the order that caused it? |
| [Twilight Struggle](https://store.steampowered.com/app/406290/Twilight_Struggle/) | A two-player Cold War struggle for global influence. | Can every contested theater and approaching objective create an understandable decision? |

Record what each opening teaches, how many interactions precede the first meaningful choice, and how the result is explained. Our differentiator must be visible in actual gameplay footage.

## 2. What is already built

- [x] Consolidated gameplay specification, documented defaults, and removal of superseded source documents.
- [x] Four playable factions; solo against computer opponents, local hotseat, and sandbox.
- [x] Simultaneous annual orders and the economic, construction, diplomacy, debt, government, and military systems.
- [x] Contested starting deployments and recoverable territorial influence.
- [x] Distinct faction objectives, consecutive-year progress, and continued play after victory.
- [x] Live resource forecasts using the same resolution rules, with costs and shortage breakdowns.
- [x] Validated portable saves and migration of the earlier prototype format.
- [x] Functional browser and desktop command interfaces with **227 Python tests** and two Godot integration suites.
- [x] Manual browser checks of core play, forecast accuracy, objectives, save/load, and a narrow viewport.
- [x] Interactive command map across all four fronts; draft coalition, share, influence, upkeep and objective projections.
- [x] Persistent desktop planning ledger, invalid-draft feedback, changed decisions, per-faction undo and reset.
- [x] Optional guidance for the first three years and instant, skippable/replayable phase-based results derived from resolution.
- [x] Atomic local campaign/draft recovery, previous valid checkpoint, corrupt-file fallback and stale-session protection; manual saves retained.
- [x] Short introduction with EU quick start, scenario selection and portable-save import.
- [x] Remember/compare/restore a draft alternative against the same current world, with undo and faction/year isolation.
- [x] Optional original synthesized sound cues, volume/test controls, 100–150% text sizes and reduced motion; preferences recover locally.
- [x] Campaign diagnostic runner with five simple policies, all factions, multiple seeds, recorded orders, outcome metrics and exact replay; 60 configurations completed and replayed.

The prototype establishes mechanical correctness for the tested cases. It does not yet establish that campaigns are balanced, the opening is engaging, opponents are challenging, or players will buy the game. Those are the next development questions.

## 3. Protect the core while improving the experience

Keep the original mechanics as intact as possible. Use the existing four factions, fronts, annual turns, resource chains, debt contracts, alliances, attrition, and objectives throughout the first polished slice.

Preserve forecast truthfulness. A more capable opponent must still produce the same response in preview and resolution for the same state, seed, and orders. Do not introduce hidden information, surprise resource grants, or random events to create tension without a deliberate design change. In hotseat, show that projections depend on drafts that other players can still edit.

Event cards and event-based policy decisions remain deferred by the user's earlier decision. Tactical battles, nuclear systems, extra factions, network multiplayer, a live service, and a new technology tree are outside the initial Steam scope. Additional scenarios, difficulty policies, or rules changes remain proposals until reconciled into `DESIGN.md`.

## 4. Immediate work package: make the opening compelling

Complete this package before committing to broad content production. Start with the existing EU opening: its economic strength, military disadvantage in Eastern Europe, and Arctic balance make the central tradeoffs visible. All rival factions continue to use the actual simulation.

| ID | Priority | Deliverable | Acceptance criteria | Depends on | Implementation status |
|---|---|---|---|---|---|
| N01 | P0 | Opening playtest and balance baseline | Observe at least 10 fresh target players; record time to first valid turn, misunderstood concepts, decisions, and reasons for stopping. Record complete campaigns and opening strategies for every faction. | Current prototype | Pending; observation sheet and scoring instructions ready |
| N02 | P0 | Interactive command-map prototype | Select any of the four fronts; inspect coalition strength, own military share, territorial influence, upkeep, and relevant objectives; edit deployments and see the forecast react. Keyboard access provides the same controls. | Existing rules and state | Implemented; engine projections and UI workflows tested |
| N03 | P0 | Persistent order and resource summary | Keep current resources, planned spending, annual changes, and expected end values available while planning. Show remaining productivity, invalid orders, and changed decisions without navigating multiple screens. Include reset/undo within the current draft. | N02 | Implemented; ledger fixed on desktop, scrollable on narrow screens |
| N04 | P0 | Guided first three years | Teach one investment, one diplomatic choice, deployments, the forecast, and objective progress using the real opening. Guidance can be skipped; the player keeps control and can make different choices. | N01–N03 | Implemented provisionally; teaching efficacy awaits N01/N07 |
| N05 | P0 | Turn-result presentation | Show treaties/orders, economy and shortages, relations, combat losses, influence, society, and objective progress in actual resolution order. Explain the three most consequential changes with links to their causes. The sequence can be skipped or replayed. | N02–N04 | Implemented; comprehension still needs player evidence |
| N06 | P0 | Automatic campaign recovery | Preserve resolved turns and editable drafts across closing/relaunching. Keep a previous valid save if writing fails; corrupted saves have a recovery path. Retain manual export/import and hotseat commitments. | Existing persistence | Implemented for the local server; scripted failure/relaunch tests pass |
| N07 | P0 | Repeat the opening test | Run the first-five-round experience with 30 fresh target players and assess the gates in section 7. Fix the leading sources of confusion before advancing. | N04–N06 | Pending fresh-player recruitment and observations |

**Opening implementation delivered:** N02 and N03 use one theater panel extended across all four fronts, connected to real drafts and the reference simulation. N04–N06 are also implemented for local testing. The 3 October improvements added an introduction, draft comparison, basic M1 audio/display settings and the M2 diagnostic harness. **Current desktop status, 4 October:** Godot now covers the existing gameplay workflows on the shared Python simulation; Streamlit remains the development client. The desktop migration and worker spike are complete. Next, establish the art direction, generate original game graphics, and polish the Godot screens using section 11, while recruiting for N01 and refining guidance/results with its evidence before N07. M1 is **not** complete without those observations and remaining presentation work.

Opening-slice evidence recorded 136 passing tests at that milestone, including solo/sandbox/hotseat forecast equality, draft comparison/undo, invalid-draft recovery, preserved hotseat handoff, preference validation, report validation, v1/v2 migration, interrupted replacements, corrupt checkpoint fallback, stale-session protection and exact campaign replay. Real-browser campaign work exposed a rerun between writing a checkpoint and storing its new token; recovery now records both inside one non-yielding operation, with a regression test reproducing that interruption. Save downloads no longer initiate a rerun. At 150% text, summary buttons use a separate row to avoid clipping. The browser workflows and current verification are in `README.md`; the [opening-slice evidence](playtests/implementation-evidence.json) retains that milestone's results.

The [2 October measurements](playtests/implementation-evidence-2026-10-02.json) retain the prior deterministic 100-year save check (about 1.28 MB within the 2 MB limit), plus serialized-input forecast timings over 20 samples: approximately 7 ms opening and 55 ms at round 101 at the 95th percentile. These historical backend measurements are **not** end-to-end minimum-hardware acceptance results for the current build.

Three [agent-authored browser campaigns](playtests/browser-playthroughs-2026-10-03.json) played EU, China and Russia for five years each, using construction, diplomacy and deployment controls. All 75 displayed resource forecasts matched resolution, each campaign recovered after the third year, and all 15 downloaded result saves matched full engine replay. No JavaScript errors remained in these completed checks. These runs found and verified the recovery/download/layout fixes above; they are separate from N01/N07's required human observations.

The opening needs an observable strategic consequence: a supply bottleneck relieved, a trade decision paying off, or a front shifting toward an objective. The tutorial must report whichever result the player's actual orders produce. It must not award a scripted victory or change the three-year hold requirement.

For N01, use [playtests/observations.csv](playtests/observations.csv): faction, seed, prior strategy-game experience, first action, time to first valid draft/resolved year, forecast understanding, military-share/influence understanding, years played, stopping reason, and willingness to try another faction. `README.md` supplies the observation/scoring procedure. Keep recordings and identifiers optional. There are no participant observations or player telemetry today.

## 5. Production milestones and exit gates

Milestones are ordered by evidence, not a promised calendar. Assign a named owner to each workstream before estimating dates. One person can cover several roles, but the responsibilities still need time and budget.

### M1 — Validated opening

Deliver N01–N07. The player can understand the current crisis, make orders, inspect consequences, resolve the year, and resume later. Provide a coherent visual treatment for the map, resource bar, and front panel, plus basic sound and volume controls.

**Exit:** the opening passes the comprehension and reliability gates in section 7. Record problems and results per build. If players do not understand their choices or want to continue, iterate this slice.

Suggested responsibilities: game design, interface design, gameplay engineering, and playtest coordination.

### M2 — Strategic depth and replayability

Replace the current fixed allocation preferences with tested opponent decisions that recognize threats, approaching victories, production bottlenecks, and useful agreements. Keep the same budgets and forecast contract. A personality should create a recognizable strategic preference with counterplay.

Build a campaign evaluation harness covering all factions and multiple seeds. Compare candidate policies against the current AI and against several simple strategies, including factory expansion, military concentration, research investment, and diplomatic cooperation. Record wins, time to victory, objective resets, shortages, debt, and unresolved campaigns. Automated victories are diagnostic; human play remains necessary.

**Harness implemented; balance work remains.** The [3 October baseline](playtests/campaign-baseline-2026-10-03.json) covers four faction labels × five policies × seeds 17/23/41, with a 30-year observation window and exact replay of every case. Each case retains initial/final saves and a hashed order transcript. The all-computer `current` policy repeats the same world trajectory for different player labels at the same seed; these are configurations, not 60 independent samples or human participants. A [representative replay](playtests/replays/EU-military-17/summary.json) is retained in the repository.

| Baseline finding | Interpretation and next experiment |
|---|---|
| 54/60 configurations unresolved after 30 years; six Chinese victories in years 26–27; no tested player policy won | Existing simple policies rarely pursue all objectives. Add candidate objective pursuit, defense and rival-denial decisions in the harness, compare against this baseline, and demonstrate a win for each faction before replacing playable AI. An observation limit is not a draw or game turn cap. |
| Factory-policy player productivity averaged 307.2 at the end; current-policy average was 28.3 | Expansion compounds strongly, but produced no own victories here. Compare objective progress, actual counters and financing before changing factory costs/output. |
| Research policies accumulated 66 tested-player shortage years across 12 configurations | Inspect operating compute/energy demand and construction choices; test a supply-aware research policy. These are policy findings, not proof of a broken resource formula. |
| Tested-player objective streaks never started | Inspect condition-by-condition progress and collect authored/human strategic campaigns. Do not lower the hold requirement to manufacture wins. |

The default computer policy, gameplay coefficients and rules identifier remain unchanged. Next balance experiments should record their hypothesis, code fingerprint, candidate policy, reproducible saves and comparison before any gameplay change is adopted.

**Objective-play follow-up, 3 October:** [PLAYTEST_REPORT.md](PLAYTEST_REPORT.md) and the [16-campaign matrix](playtests/objective-campaigns-2026-10-03/results.json) now demonstrate EU, US, and Chinese victories against the current AI using two deterministic full-objective policies at seeds 17/23. All four Russian cases remain unresolved after 45 years; this milestone's every-faction exit is therefore still open. All final transcripts replay exactly. Extra industry helped EU timing, delayed US wins, and badly strained Russian supply/finances. New synthetic probes also show full rewards for token garrisons and recovery triggered by new production even with full initial deployment. Prioritize objective-aware opponents, a viable Russian campaign, and the presence/force-finance incentives before broad coefficient changes. The client now shows post-combat objective gaps, influence blockers, victory watch, pre-commit resource warnings, and separate troop/influence map bars; fresh-player comprehension gates remain untested.

Investigate these specific balance risks before changing values:

| Risk to investigate | Evidence to collect | Candidate response if confirmed |
|---|---|---|
| Opening cash makes finance decisions feel inconsequential | How often money, upkeep, or borrowing changes a player's plan in the opening and middle game | Test scenario or cost coefficients, preserving debt mechanics |
| Factory expansion compounds into an automatic best opening | Compare economic growth and victories against alternative builds across factions and seeds | Test cost/output values and pacing |
| Large supply stocks remove meaningful production choices | Track stockpiles, facility downtime, unused compute, and player reactions to shortages | Tune production, demand, or initial stocks |
| Objective thresholds create long stalemates or one faction wins routinely | Report streak starts/resets, time to first victory, and strategic reasons for non-completion | Improve denial/defense decisions first; then test documented balance changes |
| A single repeated public-service or research investment dominates | Compare opportunity costs, content saturation, innovation, and eventual victory | Test the relevant project coefficients |
| Reserve recovery or concentrated forces trivialize attrition | Compare casualty and recovery trajectories under concentrated and distributed deployment | Test documented recovery/combat coefficients |
| Exact forecasts encourage tedious repeated optimization | Observe planning time, unnecessary edits, and whether players can compare plans easily | Improve explanations and draft comparison while preserving truthful forecasts |

**Exit:** every faction has a demonstrated path to victory against the proposed standard AI; multiple opening plans have observable tradeoffs; opponents respond to an imminent rival victory; no confirmed dominant strategy or persistent stalemate remains unexplained. Save a reproducible campaign for each finding. Set the campaign-length target using these results, not an arbitrary new turn cap.

Suggested responsibilities: game design, opponent engineering, QA, and experienced strategy playtesters.

### M3 — Desktop vertical slice and presentation

**Functional desktop migration implemented, 4 October.** The repository has a headless Python package, shared `GameSession`, separate Streamlit and Godot clients, and a versioned local worker protocol. Godot now exposes all existing command workflows: construction/projects, diplomacy, deployments, government/debt, objectives, history, full scenarios, forecasts, alternatives, reviews, guidance, presentation settings and recovery. Streamlit remains available for development. The 227 Python tests retain the original gameplay regressions and add application, protocol, scenario and presentation checks; fixed pre-migration fixtures verify unchanged results. Two real Godot scene/worker suites cover the desktop workflows, including a rendered pass. See [README](README.md#godot-desktop-client) for setup and boundaries.

**Remaining M3 work:** apply the chosen visual direction to the desktop screens, check accessible visual/input behavior, run player evaluation, and build an installable Windows release with a bundled worker (or a fixture-verified engine port). Production packaging and Steam integration are still pending. Functional feature coverage does not close the M1/M2 player and balance gates.

Produce an installable desktop build with the M1 experience and M2 behavior. The Godot/Python integration spike and command-screen migration are complete; evaluate interaction quality, packaging, accessibility, performance and maintenance cost before changing the simulation technology.

Maintain one authoritative simulation. Reuse it where practical; if a port is needed, compare both implementations against recorded state/order/result fixtures for construction, shortages, treaties, debt, combat, objectives, and saves. Define numerical tolerances per field and require identical threshold/victory decisions. Continue versioning gameplay separately from the save format: the opening slice writes rules identifier `1` with schema `3`. Reconcile and version future rule changes explicitly; a schema number alone does not identify gameplay behavior.

Create a recognizable art direction with original generated game graphics: a legible world command map, distinct faction identity, separate symbols for troops and influence, restrained motion, and readable typography. Integrate and test the assets in the playable desktop build. Use sound to mark meaningful actions and changing stakes. Preserve instant or reduced-motion turn results. Record each asset's source, prompt or creator, edits, and usage rights. Store artwork should follow after the in-game direction is validated.

**Exit:** a fresh machine can install, launch, play, save, close, and resume without development tools. The same orders produce the same results as the reference rules. Meet the performance and accessibility targets in section 7 on declared test hardware.

Suggested responsibilities: client engineering, UI/art direction, audio, build/release engineering, and QA.

### M4 — Public demo and audience validation

Build a polished EU introduction with replay and a path to continue its campaign. A 20–30-minute introductory session is the hypothesis; test actual completion time. Explain the full game's four factions using working gameplay. Ensure there is enough freedom to demonstrate a second plan. Avoid presenting a tutorial checkpoint as a full-game victory.

Prepare a store page, a gameplay-led trailer, accurate screenshots, capsule artwork, and a short press kit. The trailer should quickly show a choice, its live forecast, and the resulting world change. Use truthful footage from the build offered to players. Test working titles and capsule readability before committing to the current project name.

Use the demo to measure completion, voluntary replay, return sessions, feedback, and attributed store interest. Recruit beyond friends and existing supporters. Prepare creator outreach around distinct strategic stories; actual publication, paid promotion, and contact campaigns are later production actions.

**Exit:** repeat the player gates with a larger audience, explain the major drop-offs, and establish a measured acquisition baseline. Compare the result with the commercial model in section 8. Choose an eligible Steam Next Fest only when the demo is ready.

Suggested responsibilities: game design, community/marketing, capture/editing, art, and QA.

### M5 — Release candidate and launch

Bring all four factions and the agreed modes to the same presentation and usability standard. Complete local saves, recovery, the intended Steam features, settings, help, credits, and store disclosures. Recommended Steam features are Cloud saves and achievements tied to meaningful strategic milestones; these are product proposals, not universal release requirements. Test Cloud conflict and offline recovery before advertising support.

Choose launch languages using actual audience demand; externalize text before commissioning localization. Test long strings, number formats, tutorial layout, and rule explanations. Add Steam Deck/controller or other platform support only when it has an owner, budget, and verified build.

Run campaigns on the supported hardware matrix, upgrade old saves, and test offline play, interrupted writes, display scaling, and installer updates. Draft release notes and player support instructions. Prepare rollback builds and a named responder for release problems.

**Exit:** no known release-blocking crash, save loss, invalid order exploit, objective error, or preview/result mismatch; the promised features pass QA; store and build approvals are complete; launch support and the commercial decision are funded. A chart result is measured after release, never assumed before it.

Suggested responsibilities: release engineering, QA, localization, community support, marketing, and product ownership.

## 6. Steam preparation and timing

The following platform facts were checked against Valve documentation on **2 October 2026**. Recheck the selected event's rules and deadlines when scheduling; platform minimums are not enough time to build an audience.

- Plan for the Steam Direct waiting period: Valve specifies 30 days between payment of the app fee and release for the first few titles, and a public Coming Soon page for at least two weeks. [Steam Direct](https://partner.steamgames.com/steamdirect)
- Complete both store and build checklists and reviews. Submit store presence before the build review. Valve describes a typical store review of 3–5 business days and recommends submission at least seven days before the intended page launch; budget time for corrections. Release is a deliberate publisher action after approval. [Steamworks: Release Process](https://partner.steamgames.com/doc/store/releasing)
- Publish a Coming Soon page once representative gameplay and assets support a credible pitch. Track wishlist additions, deletions, and purchases over time and after promotion. [Steamworks: Wishlists](https://partner.steamgames.com/doc/marketing/wishlist)
- Next Fest currently requires an unreleased base game with a public store page and a publicly playable demo. A title can participate only once; an Early Access release also changes eligibility. Select the edition after validating the demo and consult that edition's registration and build-review deadlines. [Steamworks: Steam Next Fest](https://partner.steamgames.com/doc/marketing/upcoming_events/nextfest)
- Use attributed store links and Steam's reporting where available. Record attribution limitations and consent-related missing data; store traffic is not equivalent to demo players or purchases. [Steamworks: UTM Analytics](https://partner.steamgames.com/doc/marketing/utm_analytics)

Practical sequence: establish publisher/account readiness and budget → validate the pitch → publish representative Coming Soon materials → run private playtests → publish the polished demo → participate in the selected event → reassess demand → finish release QA and reviews → launch. Schedule review submissions around the actual event deadlines, which can precede the demo's public release.

## 7. Quality targets and measurement

All numbers below are **proposed internal targets**, not Steam requirements, genre averages, current results, or predictors of a top-10 rank. Revisit them after the baseline, recording the rationale. Report the numerator, denominator, build, recruiting source, and observation window; small samples are directional evidence.

| Area | Initial target | How to check |
|---|---|---|
| Opening comprehension | At least 24 of 30 fresh target players resolve the first year without facilitator help within 10 minutes | Observe M1; in-game guidance is allowed, developer coaching is not |
| Forecast understanding | At least 24 of 30 can explain one resource change and distinguish military share from territorial influence | Ask after their first resolution; score against a prepared rubric |
| Continued play | At least 21 of 30 voluntarily reach five resolved years within a 30-minute observation window | Include early exits in the denominator; do not require five turns as a participation condition |
| Replay interest | At least 12 of 30 start another plan/faction or return within seven days when access remains available | Measure actual behavior with consent, not just stated intent |
| Resolution clarity | At least 24 of 30 identify their main gain/loss and the decision or system that caused it | Ask after a later turn, without explaining the answer first |
| Forecast correctness | No mismatch in supported deterministic scenarios beyond documented numeric rounding | Compare current draft forecasts with actual resolution, including save/load and AI changes |
| Strategic viability | Reproducible winning campaigns for each faction; documented competing openings and counters | Human campaigns plus automated evaluation; do not assume equal 25% win rates for asymmetric factions |
| Responsiveness | Forecast update at the 95th percentile under 250 ms; resolution under 1 s before presentation | Measure end-to-end on a declared minimum-spec candidate over opening and late-game states; these are unverified targets |
| Recovery | All scripted close/relaunch, interrupted-write, corrupt-save, and migration scenarios recover as designed | Keep previous valid saves; include drafts and hotseat submissions |
| Accessibility | Core loop usable with keyboard; no essential color-only meaning; scalable text; motion/audio controls | Test at 1280×720 and 1920×1080 with scaling; add supported-device checks before advertising them |

For a public demo, also report unique starts, first-turn completion, five-turn completion, median active playtime, return sessions, and feedback reasons. Separate new and returning players and exclude idle time from active playtime. Do not infer that someone bought or wishlisted from an in-game button click. The eventual collection method must be explicit and compatible with offline play.

At every milestone, retain a short evidence record: build/rules version, cohort, observations, results, top three problems, chosen fixes, and the decision to advance or iterate. The current automated tests remain a correctness baseline; player evidence answers different questions.

## 8. Commercial validation and resourcing

Set a budget for a defined milestone before broad production. Cover gameplay/client engineering, UI and art, audio, playtesting, QA, localization, store assets, marketing, and post-launch support. Team capacity, available funding, and schedule are currently unknown, so this document does not promise a release date or total cost.

Prepare conservative, central, and upside sales cases using explicit assumptions and a stated time horizon, such as launch week and the first year separately:

`estimated units = prelaunch wishlists × assumed purchase conversion + estimated purchases from other sources`

`estimated contribution = units × estimated net receipts per copy − remaining production, launch, and support costs`

Net receipts must account for the planned price, regional sales mix, discounts, refunds, taxes, and distribution terms. Avoid double-counting people reached through multiple channels. Before there is purchase evidence, conversion is an assumption with a range, not a measured fact. Replace it as actual data becomes available. No scenario should assign a guaranteed chart rank.

Track the costs and observed results of each demo/store campaign before increasing spend. There is no universal wishlist quota in this plan. Set a project-specific demand gate after estimating break-even units and a credible audience funnel, then record it before authorizing full production.

Make the release-model decision after demo evidence. A full release is the working preference for a focused, complete strategy game. Consider Early Access only with a satisfying playable product, a specific development purpose, and a funded update plan; account for Next Fest eligibility when sequencing it.

After launch, track revenue, units, refunds, reviews, crash/save issues, completed campaigns, and repeat play. Prioritize reliability and the main recurring player complaints before adding systems. Keep a tested rollback path and a staffed support channel through the launch window.

## 9. Decisions to make at the appropriate gate

These decisions do not block the first command-map and forecast improvements.

| Decision | Working recommendation | Resolve before |
|---|---|---|
| Meaning of Steam top 10 | Global real-time revenue chart, rank ≤10 during launch week; weekly result reported separately | Commercial launch targets |
| Target audience and pitch | Approachable geopolitical strategy with visible consequences and asymmetric objectives | Public store page |
| Final name and visual identity | Test a distinctive name and map presentation using the real opening | Final capsule/trailer production |
| Team, budget, and available work time | Fund and staff the next evidence gate first | Production estimates and external commitments |
| Desktop client and simulation integration | Godot 4 with a local Python worker; all current gameplay controls connected | Visual polish, release packaging and any future C# port |
| Campaign length and difficulty | Derive targets from all-faction playtests; preserve exact forecasts | M2 sign-off |
| Price, languages, and release model | Use scope, audience evidence, and the cost model | Paid store positioning and release scheduling |
| Additional platforms and controller support | Windows first as a planning assumption; add verified targets deliberately | Promising support publicly |

## 10. Definition of the next completed milestone

The next milestone is complete when a new player can open the game, understand the EU's position, make an investment and military/diplomatic choices, see their resource consequences, resolve the year, explain the result, and safely return later—and the M1 playtest evidence meets the recorded gates.

Update this roadmap with evidence as tasks complete. Update `DESIGN.md` for every accepted gameplay change and `README.md` for runnable capabilities. Keep speculative features, delivery estimates, and commercial goals here until they are validated and implemented.

## 11. Visual polish and graphic generation

**Immediate focus:** make the functional Godot command desk feel like a cohesive strategy game. The current desktop screens, schematic map, generated introductory art, and forecast/result feedback provide the working reference. First agree a compact art direction and asset brief; then generate original graphics, integrate them in-game, and polish the screen hierarchy. Use Streamlit as the development reference and the Python simulation/replays as the source of truth. Graphics remain presentational and cannot imply mechanics the game does not simulate.

| Order | Concrete work | Acceptance check |
|---|---|---|
| G1 · Art direction and screen hierarchy | Set the Godot palette, typography, spacing, faction colors, icon style, and treatment of forecasts, warnings, and results. Define one small reference screen and a written brief before generating a full asset set. Reduce repeated panels and keep the command desk readable at game-window sizes. | A one-page visual brief and an in-game reference screen establish reusable choices. Meaning remains clear without color alone. Primary orders, current state, and expected consequences are easy to distinguish. |
| G2 · Generate original game graphics | Generate a coherent set of in-game assets: four faction identity illustrations or emblems, resource and facility icons, and a world-map/theater graphic that retains the game's abstract fronts. Create size/crop variants only where a real screen needs them. Track prompts, source files, edits, and rights alongside the assets. | Assets share a style, remain readable at UI size, work offline, and introduce no false borders, units, or game rules. Every asset has provenance and a clear usage grant. The same assets appear in the running client, not just in mockups. |
| G3 · Integrate and polish Godot screens | Apply the generated assets and visual system to campaign setup, Situation, Economy, Diplomacy, Military, Objectives, Chronicle, and the turn review. Tighten selected-front, forecast, resource, and victory hierarchy; keep detailed ledgers accessible. | All screens use the same visual language. Controls remain responsive with all assets loaded; keyboard focus and reduced-motion settings work. Record reference captures from the actual playable build. |
| G4 · Accessibility and layout pass | Check contrast, focus, label clarity, asset scaling/cropping, dense tables, and smaller supported windows. Preserve simple shapes and text alongside faction colors. Keep motion restrained and results skippable. | Test at 1280×720 and 1920×1080 with 100%, 130% and 150% text. No essential information is clipped, color-only, or embedded solely in an image. Keyboard users can reach every primary order and recovery action. |
| G5 · Playtest and production art | Use N01/N07 observations to refine the interface and determine which images help players understand the crisis and consequences. After the in-game direction is validated, generate store screenshots, capsule concepts, and trailer frames from the tested build. | Fresh players can explain an order's consequence and separate troop share from influence. Store material depicts the playable game accurately. Keep originals, prompts, final files and rights records together. |

Keep graphics work offline and reproducible. Retain generated source images and provenance metadata so crops or style variants can be regenerated. For each integration pass, save before/after screenshots and verify the keyboard, text scaling, forecasts, recovery, and presentation on the Godot build. Do not treat a polished mockup or generated image as evidence that the game is balanced or the opening is understood.
