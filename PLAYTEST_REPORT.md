# Game improvements and objective-driven playtests

3 October 2026. Rules version **1**, save schema **3**. These are scripted strategic experiments and browser checks, not human-player research.

**Implementation update, 4 October 2026:** the Godot desktop client now covers the gameplay workflows described here, using the same Python simulation and forecasts as Streamlit. Its functional integration checks passed, including a rendered pass. The graphics and interface are still at prototype quality. Original visual assets and desktop polish are the next work; they have not been evaluated by new human players, and do not change the campaign results below.

## What improved

- **Objective planning:** every condition now compares the resolved world with the exact post-combat forecast. The screen shows the remaining gap, conditions newly met or at risk, expected hold advancement/reset, and advice specific to the objective. Small nonzero gaps retain enough precision to explain why a condition still fails; strict thresholds explicitly reject equality.
- **Explain the EU's main obstacle:** the Russian-influence condition identifies surviving coalitions that block new influence. Having a security majority and removing established Russian influence are visibly separate tasks.
- **Fewer navigation steps:** each objective links directly to its theater without changing orders or advancing time.
- **Victory watch:** compare all four factions' current and expected conditions and holds. Influence mode checks the leading total, including ties; open mode never predicts a winner. Already secured victories remain permanent.
- **Before committing:** surface expected shortages, operating deficits, new borrowing, expiring productivity, hold resets, and imminent victories beside the end-year control. Invalid plans clear predictions. Hotseat forecasts remain conditional on other drafts.
- **More informative graphics:** each theater has separate troop-share and influence bars, an unclaimed-influence segment, actual resolved status, a faction legend, and numerical descriptions. Selection has a neutral accent so territorial influence is not mistaken for military leadership. Keyboard control remains available. The map pans horizontally on narrow screens instead of shrinking its text into illegibility.
- **Better evaluation tools:** added `objective` and `objective-industry` policies, per-condition campaign records, maximum progress statistics, and replayable full campaigns. Added a small deterministic balance-probe tool.

The simulation coefficients, faction objectives, three-year hold, starting assets, and standard AI are unchanged. This pass improves planning and establishes evidence for the next balance changes. The earlier low win rate did not justify simply lowering victory thresholds: focused play now wins with three factions under the existing rules.

## How the games were played

The final matrix uses all four factions, two authored policies, and seeds **17 and 23**, against the existing solo opponents. Each game runs until first victory or **45 resolved years**. The observation limit is not a draw or a new turn cap. Every campaign retains an initial save, all four factions' actual orders, per-year state hashes and objective values, a final save, and a summary. All 16 transcripts were replayed exactly.

Player orders are deterministic and directed at the complete objective set. Seed variation comes from the existing computer opponents, not random player actions. The policies:

1. Offer trade, use zero tariffs, and improve selected relations to obtain economic benefits. EU seeks a US military alliance; other factions avoid allies diluting the national shares required by their objectives.
2. Set taxes to 40%, or 55% for Russia. Build a limited factory base, then military production and supporting energy/compute facilities. Russia also attempts GDP investment before its finances deteriorate.
3. Compare a fixed grid of mobilization levels and front splits through the real resolution engine. Also search for smaller deployments that meet the relevant post-combat conditions. These are the same public forecasts the player can inspect, with no altered resources or combat rules.
4. Prefer own victory, avoid an immediate rival victory, penalize rival hold progress, and weigh casualties, upkeep, and borrowing. The search considers relevant theaters, rather than exhaustively optimizing every possible action.

The regular policy targets six added factories for EU/US/China and three for Russia; the industry variant targets twelve and six respectively. These are policy targets, not guaranteed completed buildings. Seed 17 was used during exploratory policy development; seed 23 was held out until the final matrix. The variants share most of their logic, so this is a focused comparison, not a broad sample of independent strategies or an estimate of human win rates.

## Results

**16 games, 360 resolved years, 12 player victories, four unresolved campaigns.** Every winning campaign had zero supply-shortage years. One winning run used new borrowing: EU industry, seed 17, approximately **0.016 T**. Every winning faction began one objective streak and completed it without a reset.

| Faction | Objective policy, seed 17 | Objective policy, seed 23 | Industry policy, seed 17 | Industry policy, seed 23 |
|---|---:|---:|---:|---:|
| EU | Won, year 24 | Won, year 23 | Won, year 22 | Won, year 22 |
| US | Won, year 10 | Won, year 10 | Won, year 11 | Won, year 11 |
| China | Won, year 12 | Won, year 12 | Won, year 12 | Won, year 11 |
| Russia | Unresolved at 45 | Unresolved at 45 | Unresolved at 45 | Unresolved at 45 |

“Year 24” means the 24th resolved annual turn, not the calendar year 2024. Full results: [objective campaign matrix](playtests/objective-campaigns-2026-10-03/results.json).

For comparison, I also ran the existing factory-only and single-front military policies for all four factions at seed 17, with the same 45-year window. **None of those eight policies won its own campaign**; five stayed unresolved, two lost to China, and one lost to the EU. Those comparison games were replay checked during execution; their [aggregate results](playtests/comparison-45-years-2026-10-03.json) are retained. The full replay archive retained in this repository is the new objective matrix.

### EU: a real recovery campaign, but a long one

The EU's moderate plan first started its hold in year 22 at seed 17 and won in year 24. The industry plan started in year 20 and won in 22. At victory, the moderate plan retained **37.12 T**, while the industry plan retained only **2.67 T**. More industrial capacity bought time at a substantial financial cost.

This demonstrates a recoverable route through all three EU objectives. It also exposes a pacing issue: a player can achieve strong military shares long before they can remove the Russian influence that prevents the hold from beginning. The new blocker explanation helps, but may not be enough to make that interval engaging.

### US: opponents abandon one of its objectives

Both moderate plans won in ten years; extra industry delayed the win to eleven. The current EU, Chinese, and Russian AI weights put no forces in South America. Their opening foreign deployments withdraw on the first resolution, so the US can fulfill that objective without defending it. Subsequent effort goes into Arctic dominance and Pacific containment.

This is evidence for better opponent decisions before changing US thresholds. A useful opponent should sometimes contest South America or otherwise disrupt an imminent US hold.

### China: fast victory is possible without a sustainable budget

China won in eleven or twelve years with both plans. It supported its facilities and split forces between its two required fronts instead of merely winning one theater. However, the moderate victories ended with operating deficits of about **6.6 T/year**, and the industry victories around **6.7–10.1 T/year**. Existing cash covered the bills through victory.

Winning a short campaign does not show that the final position can finance itself indefinitely. The new operating-deficit warning makes that tradeoff visible. Any future longer campaign should test whether the same strategy collapses after its treasury buffer runs out.

### Russia: finance and force commitment remain unresolved

Neither policy began a hold or met the Eastern European condition. At seed 23, Russia briefly met its Arctic condition: year 14 with the moderate policy, and years 9–10 with the industry policy. The conservative policy often withheld forces to avoid paying for a partial position that did not approach the 99% Eastern European requirement. This is a limitation of these policies as well as evidence of an asymmetric challenge; it does **not** prove Russia is unwinnable.

| Russian outcome after 45 years | Moderate, seed 17 / 23 | Industry, seed 17 / 23 |
|---|---:|---:|
| GDP, T | 6.21 / 6.12 | 2.50 / 2.12 |
| Total debt, T | 0.58 / 2.48 | 2.63 / 9.40 |
| Supply-shortage years | 5 / 6 | 31 / 34 |
| New borrowing, T | 0.13 / 2.03 | 2.18 / 8.95 |

At seed 17, the moderate policy accumulated **17,780 military power**, much of it idle. The industry variant used more productivity on drones but repeatedly failed to support its facilities and income. The lesson is not “always build factories”: Russia needs a viable fiscal and supply path to converting its reserve into a successful offensive.

## Balance choices evaluated

### Keep the three-year hold for now

The hold gives rivals time to respond and is achievable for three factions. No winning run suffered a hold reset, which points toward weak opponent interruption. Lowering the hold would make those wins easier without addressing Russia's position. Test adaptive opponents before changing this requirement.

### Factory growth is strong, but opportunity costs matter

The additional factory opening helped the EU by one or two years, delayed US victory, had mixed small effects for China, and damaged Russia. The old factory-only policy also grew rapidly without winning. These results do not establish factories as a universal dominant strategy, so a blanket factory nerf would be premature.

### Troop-share objectives and uncontested influence use very different scales

A deterministic synthetic probe placed **1,200 EU power against 100 Russian power** in Eastern Europe. Russia retained **0.1 power**, blocking all influence gain. Raising the EU force to **1,202** eliminated the opponent and gained ten influence. This follows the existing attrition formula and Russian damage reduction; it is not rounding in the objective check.

With the original eastern influence totals, the EU then needs six uncontested gains to reduce Russian influence from 45 to at most 10: two gains fill unclaimed territory and four displace Russian influence. The three-year hold only starts when all conditions pass. The contrast between a 60% security objective and roughly 12:1 forces for immediate clearance deserves explicit explanation and pacing experiments.

### Token garrisons receive outsized rewards

In a separate synthetic scenario with all other forces withdrawn, **0.01 US power on each of four fronts** earned **4.08 T** of annual dominance income and **40 influence**, for **0.0002 T** of deployment upkeep. These are real rules applied to an isolated scenario, not a result from an ordinary campaign. Percentage-only dominance and fixed influence gains give almost-free rewards wherever an opponent leaves a front empty.

### Reserve accumulation is too easy to ignore

New military production enters reserve before recovery is calculated. A probe with 300 current US military and 400 capacity recovered **4.498 power** whether it initially deployed zero or all 300, because that year's 49.8 new power created reserve in either case. Recovery therefore does not necessarily reward deliberately holding back existing troops.

The campaign policies also accumulated large armies: EU victories reached about 11,000–15,000 power, and Russia could hold roughly 18,000 mostly idle. Drone construction has no direct currency cost and reserves have no monetary upkeep. Conversely, mobilizing these stocks can cause enormous recurring bills. In the old single-front comparison, the US finished with over 2,200 T of debt and China over 2,800 T while remaining operational. Automatic borrowing prevents immediate failure but permits economically implausible military trajectories.

Probe inputs and outputs are retained in [balance-probes-2026-10-03.json](playtests/balance-probes-2026-10-03.json), reproducible with `python -m tools.probe_balance`.

## Further improvements, in priority order

| Priority | Improvement to test | Why; how to judge it |
|---|---|---|
| 1 | Give standard opponents complete-objective planning and imminent-victory denial | All 12 winning streaks completed uninterrupted. Use the experimental policy as a reference, then implement a bounded-cost opponent. Check forecast determinism, response time, multiple seeds, and counterplay; do not promote the policy unchanged, since it still fails Russia. |
| 1 | Author a viable Russian campaign and test alternative fiscal plans | Compare infrastructure first, debt/interest management, government choices, diplomacy, and timed mobilization. Record a reproducible win or identify the actual binding mechanic. Only then test starting-income or objective-threshold changes individually. |
| 1 | Make economic/control rewards depend on meaningful presence | Compare a minimum effective garrison with a continuous presence factor for dominance income and influence. Tiny forces should not receive full rewards; normal deployments should remain legible and worthwhile. Test all victory modes and opening factions. |
| 2 | Test the military stock/finance loop | Compare modest reserve maintenance, recruitment costs, and recovery tied to reserve present before production, one change at a time. Track total and idle forces, operating budgets, shortages, and victory times. Avoid making Russia's fiscal problem worse without a compensating viable path. |
| 2 | Explain and test the influence stalemate interval | Add a forecast of remaining opposing coalitions and approximate sustained clearance needs. Compare the existing uncontested rule with carefully bounded influence pressure under overwhelming dominance. Preserve a meaningful distinction between military share and territorial control. |
| 2 | Offer editable objective plans and construction completion controls | Let players preview a suggested front allocation through draft comparison, and fund the remaining work for one facility with a clear startup cost. Keep controls undoable and respect committed hotseat drafts. Check whether this reduces trial-and-error editing. |
| 3 | Improve map readability further | Add faction patterns or symbols to supplement color, and a carefully labeled Current / Planned / After combat view. Use subtle cues for threatened holds. Check keyboard descriptions, focus visibility, contrast, 150% text, and mobile panning with actual players. |
| 3 | Reduce scrolling and improve campaign pacing feedback | Test a compact command layout, a direct route to the commit area, and a short objective trend chart. Explain why an apparently strong position is not progressing. Prioritize these over decorative textures, flags, or combat animation. |

No paid art, external map service, new dependency, or generated raster asset is needed for the current improvements. The existing schematic SVG is a good fit for the abstraction. More attractive art should follow decisions about information hierarchy and readability.

## Reproduce and inspect

```bash
# New output directory required; existing experiments are preserved.
.venv/bin/python -m ww3.evaluation run \
  --output /tmp/ww3-objective-review \
  --policies objective objective-industry --seeds 17 23 --turns 45

.venv/bin/python -m ww3.evaluation replay \
  playtests/objective-campaigns-2026-10-03/EU-objective-17

.venv/bin/python -m tools.probe_balance
.venv/bin/python -m pytest -q
```

Saved `initial.json` and `final.json` files can also be imported through **Save / load game**. The final matrix's source fingerprint is stored in its results file. Replaying uses recorded orders, not a fresh AI decision.

**Validation: 166 automated tests passed; the real-browser regression passed with no JavaScript errors.** Checks cover forecasts, objective navigation, invalid plans, undo, comparison, saves, keyboard map selection, desktop/narrow layouts, selection centering after resize, text scaling, sound, and turn review. The retained legacy campaign also still replays exactly. Details and source hashes are in [improvement evidence](playtests/improvement-evidence-2026-10-03.json).

Visual records: [desktop map](playtests/captures/improvements-2026-10-03/map-1920x1080.png), [narrow map](playtests/captures/improvements-2026-10-03/map-390x844.png), [objective planning](playtests/captures/improvements-2026-10-03/objectives-1280x1400.png), and [150% text](playtests/captures/improvements-2026-10-03/large-text-150.png). See [README.md](README.md) for browser commands. These checks establish functional behavior; fresh human sessions are still needed to establish whether the explanations, campaign length, and difficulty are enjoyable.
