# Geopolitics / WW3 — Authoritative Game Design

This is the single source of truth for gameplay. It consolidates the original **Geopolitics: WW3** document, the supplemental **Global Factions / World Order** summary, and the user's decisions. The superseded input files have been deleted after consolidation.

**Status, 3 October 2026:** the rules below are the implemented local prototype baseline. The commercial ambition is a Steam top-10 game. [NEXT_STEPS.md](NEXT_STEPS.md) describes proposed development, player validation, and release milestones; it does not override these rules. [README.md](README.md) records the implementation status and how to play. This design stays independent of implementation technology.

## 1. Scope and confirmed decisions

A turn-based geopolitical strategy game with four playable factions: **EU, US, China, and Russia**. The focus is economic, diplomatic, and military decisions with a readable strategic world map. Combat is abstract; there is no tactical battlefield or geographical conquest system.

Confirmed decisions:

- Play one faction against three computer opponents, with optional local hotseat. A sandbox can control all four factions.
- The original document takes precedence where the two source documents conflict. The summary supplies missing rules. Remaining gaps use the explicit, configurable defaults in this document.
- Forces remain deployed, can be reassigned, and suffer simultaneous losses. Allies present in the same theater combine for combat.
- **Territorial influence grows only when a front is uncontested**, including a battle that leaves one surviving coalition. Contested military dominance can still grant the summary's tax bonuses.
- EU victory requires lasting European security, recoverable Russian territorial influence, and Arctic balance. A European security coalition may include allies.
- The opening scenario has deployed forces and established influence that create contests around faction objectives. No faction begins with all objectives satisfied.
- Default victory requires all faction objectives to hold for **three consecutive completed rounds**. An announced victory is permanent; players may continue the simulation. Open-ended and total-influence modes are also available.
- Show expected resource changes for the current turn's choices before commitment, including costs, production, shortages, and projected opponent responses. Forecasting never advances the world.
- Event-based policy decisions remain deferred, following the original “DO LATER” instruction.

All numerical defaults below are part of this design. Later changes should update this document alongside the game.

## 2. Time, orders, and information

One full round is one year; the default scenario begins in **2026**. All factions plan from the same resolved world. Planning does not advance time. Human orders remain editable until committed; hotseat players can reopen a commitment before resolution.

An annual resolution proceeds in this order:

1. Validate all orders. An invalid plan leaves the entire world unchanged.
2. Resolve mutual trade/alliance offers and update policies, tariffs, shared benefits, and deployments.
3. Pay discretionary costs from existing reserves: outreach, foreign aid, domestic repayment, foreign repayment, then construction/projects. Credit incoming aid and principal only after all factions have paid their orders. Renew matured contracts.
4. Produce minerals, consume thermal fuel, produce energy, operate facilities, produce compute, ration shortages, produce innovation/military, and recover eligible reserve strength. Set the new productivity budget. Collect tax/trade income and pay interest/upkeep; issue domestic debt only if treasury would become negative.
5. Update diplomatic relationships, then resolve all fronts with simultaneous losses.
6. Settle citizen content, GDP growth, and government transitions. Check objectives against the resulting world.
7. Advance to the next year and prepare new editable orders.

Initial assets appear exactly as specified below, without an extra opening tax payment or battle. Facilities completed in a year's orders operate during the ensuing economic update. Government effects remain those of the outgoing government through the final transition year's production; the new government's productivity modifier applies to the next planning budget.

All resolved assets, relations, deployments, and influence are public. There is no fog of war. Diplomatic offers are visible. Solo opponents prepare their next orders when the player ends the year. Hotseat is a shared-information game, with a handoff screen between players.

Taxes, tariffs, unaccepted or active treaty offers, shared benefits, and surviving deployments persist. Investment allocations, outreach, aid, repayments, and renewal-rate instructions reset after each year. **Unused productivity and compute expire.** Construction progress persists.

## 3. Factions and starting assets

Currency, GDP, and debt use **trillions of USD (T = 10¹² USD)**. Energy uses PJ; rare minerals use tonnes. Compute is abstract FLOP capacity: the source specifies +10 per data center without a physical FLOP scale. Content is 0–100. Innovation and military power are abstract points.

| Starting parameter | EU | US | China | Russia |
|---|---:|---:|---:|---:|
| Treasury, T | 60 | 50 | 40 | 10 |
| GDP, T | 20.0 | 27.2 | 17.1 | 2.0 |
| Tax rate | 40% | 25% | **20.4%** | 26% |
| Total debt, T | 16.3 | 38.0 | 16.2 | 0.45 |
| Domestic debt share | 80% | 80% | 90% | 90% |
| Foreign debt share | 20% | 20% | 10% | 10% |
| Creditor weight | 30% | **41%** | **24%** | 5% |
| Citizen content | 60 | 75 | 80 | 74 |
| Available productivity | 10 | 12 | 15 | 8 |
| Energy stockpile | 10 | 20 | 15 | 30 |
| Mineral stockpile | 5 | 5 | 20 | 10 |
| Innovation | 5 | 8 | 6 | 2 |
| Available compute | 0 | 0 | 0 | 0 |
| Military power and initial capacity | 120 | 400 | 200 | 200 |

Initial productivity includes starting national and government modifiers; those modifiers are not applied twice. It represents the pre-existing industrial base. New factories add productive capacity as defined in section 5.

Starting governments and roles:

- **EU — Democratic/pluralistic:** balance internal interests, industrial dependence, and security in Eastern Europe. A wealthy treasury supports a comparatively small military.
- **US — Democratic/oligarchic:** balance large debt, external commitments, and political change. A computer-controlled US starts a transition toward authoritarian/dictator in round two; a human US player chooses freely.
- **China — Authoritarian/one-party:** maintain citizen content and build trading partners' reliance on its manufacturing advantage.
- **Russia — Authoritarian/dictator:** support a large military with a small economy and contest Eastern Europe and the Arctic.

Relations use the original **1–5 scale** and are symmetric:

| Pair | Relationship |
|---|---:|
| EU–US | 4 |
| EU–China | 3 |
| EU–Russia | 2 |
| US–China | 2 |
| US–Russia | 3 |
| China–Russia | 4 |

There are initially no trade agreements, military alliances, tariffs, or shared trade benefits. An alliance does not happen automatically because relations are friendly.

### Opening military deployments

These deployments are scenario defaults added to make the agreed objectives meaningful. National totals remain those of the original document.

| Faction | Eastern Europe | Pacific & South China Sea | Arctic | South America | Reserve | Total |
|---|---:|---:|---:|---:|---:|---:|
| EU | **60** | 0 | 20 | 0 | 40 | 120 |
| US | 0 | 140 | 60 | 60 | 140 | 400 |
| China | 0 | 110 | 30 | 10 | 50 | 200 |
| Russia | **80** | 0 | 50 | 10 | 60 | 200 |

### Opening territorial influence

Influence represents existing political control; it is separate from troop shares. Each front has at most 100 influence, with the balance unclaimed. These are added scenario defaults. Existing Russian influence gives the EU something recoverable to roll back.

| Front | EU | US | China | Russia | Unclaimed |
|---|---:|---:|---:|---:|---:|
| Eastern Europe | 35 | 0 | 0 | 45 | 20 |
| Pacific & South China Sea | 0 | 40 | 45 | 0 | 15 |
| Arctic | 10 | 25 | 15 | 30 | 20 |
| South America | 0 | 60 | 10 | 10 | 20 |

### Opening facilities

Neither source specifies facility counts. These defaults give each faction an operating supply chain. The factory count tracks new expansion of the industrial base; the initial productive base is already represented by the starting productivity table.

| Faction | Renewable | Thermal | Data center | Drone | Cyber | Mine | Expansion factory | Research |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EU | 3 | 2 | 4 | 1 | 1 | 2 | 0 | 2 |
| US | 3 | 4 | 6 | 3 | 3 | 3 | 0 | 3 |
| China | 3 | 5 | 4 | 3 | 2 | 4 | 0 | 2 |
| Russia | 1 | 3 | 1 | 2 | 1 | 4 | 0 | 1 |

Opening innovation already includes historical construction; starting data centers do not award another completion bonus.

## 4. National traits and government

The original trait definitions take precedence over altered versions in the summary:

- **EU, Home of the chip machine:** +10% innovation gain; −25% data-center construction costs. Trade with the EU automatically shares the construction discount. **Luxury exports:** income equal to 1% of the combined GDP of the other factions per year. This coefficient comes from the summary and is not reduced by tariffs.
- **US, Home of the hyperscalers:** −20% compute consumption; this can be offered to trading partners. **Media dominance:** positive diplomatic effects are 10% stronger; negative content effects are reduced by 10%.
- **China, Factory of the world:** +20% productivity, which can be offered to trading partners. **AI superpower:** +10% innovation gain.
- **Russia, Resource rich:** +20% energy and mineral output. **Battle hardened:** reduce opposing military actions' damage by 10%. This is not a +10% ownership share or extra troops.

The summary's additional US data-center discount and Chinese −10% production-cost trait are not adopted: the original trait definitions remain authoritative. A faction's own trait does not stack with an identical imported copy. US and Chinese benefits require both an active trade agreement and explicit permission from the provider. EU's trade discount is automatic. Russia's resource/combat traits are not transferable.

Government changes last **three years**, with **5 discontent** in each transition year, including the first and last. A transition cannot be cancelled or redirected midway. National traits remain attached to the faction. Government modifiers fill an original design gap:

| Government | Productivity multiplier | Innovation multiplier | Content formula adjustment |
|---|---:|---:|---:|
| Democratic/pluralistic | 1.00 | 1.10 | +1 |
| Democratic/oligarchic | 1.00 | 1.05 | 0 |
| Authoritarian/one-party | 1.10 | 1.00 | −0.5 |
| Authoritarian/dictator | 1.05 | 0.95 | −1 |

## 5. Construction, production, and supply chains

Players allocate this year's productivity to any combination of facilities and projects. Resource costs are paid when a unit starts; partial work is stored as a completion fraction. A later discount affects work needed for the remaining fraction without charging the resource costs again. Multiple units of the same type can complete in one year. Unfinished units have no production or maintenance and cannot be scrapped or refunded.

Allocations remain drafts until **End year**. Completed facilities participate in production and upkeep during that same resolution; remaining resources and new capacity are available for the next planning turn. Partial work stays paused until the player assigns more productivity in a later year: annual allocations reset, and time alone never advances construction. Projects apply their benefits on completion during resolution.

The following are **base costs and outputs before modifiers**. Facilities are processed in the table's order, followed by the projects in their listed order. Each category uses the costs calculated when processing that category begins.

| Facility | Productivity | Currency, T | Minerals | Annual output | Annual upkeep |
|---|---:|---:|---:|---|---|
| Renewable facility | 10 | 0.5 | 5 | `5 + 0.1 × innovation` energy | 0.1 T |
| Thermal plant | 10 | 1 | 0 | 5 energy | 0.1 mineral |
| Data center | 10 | **2** | **2** | 10 compute | 1 energy |
| Drone facility | 10 | 0 | 3 | `10 × (1 + innovation/100)` military | 3 energy |
| Cyber warfare lab | 10 | 0.5 | 0 | `5 + 0.1 × innovation` military | 5 compute |
| Mineral mine | 10 | 0.5 | 3 | 5 minerals | Permanent −1 in the content formula |
| Factory | 10 | 1 | 0 | +5 base productivity capacity | 0.1 T |
| Research lab | 10 | 0.75 | 2 | `0.5 + content/100` innovation | 1 energy + 5 compute + 0.1 T |

Data-center completion grants **+1 innovation once**, subject to innovation modifiers. Its unspecified construction inputs and the one-time timing come from the summary. Drone output retains the original's innovation dependence. Research labs are referenced in the original metrics; their costs/output are added defaults.

Repeatable projects fill the original's unspecified project system:

| Project | Productivity | Resource cost | Completion effect |
|---|---:|---|---|
| Research program | 10 | 0.2 T + 5 compute | `2 × (0.5 + content/100)` innovation before modifiers |
| Public services | 10 | 0.25 T | +3 persistent civic support and +3 immediate content, capped at 100 |
| Infrastructure | 20 | 0.5 T + 1 mineral | +0.25 T GDP |
| Military modernization | 10 | 0.25 T + 2 minerals + 3 energy | `10 × (1 + innovation/100)` military and capacity |

Production/cost interpretations:

- Innovation reduces currency and mineral construction/project costs by 0.1% per point, capped at a 30% reduction. It does not reduce productivity or upkeep. This fills the original's cost-efficiency rule.
- EU's 25% data-center discount applies to currency, minerals, and productivity. The work cost is therefore 7.5 points when eligible. The US compute discount affects compute consumed by facilities and projects.
- Innovation gains from research, programs, and data-center completion multiply by the government modifier and the EU/China national modifier.
- Annual productivity is `(legacy base + added factories × 5) × current productivity modifiers`. The legacy base is calibrated so the starting table is exact: divide starting productivity by that faction's initial national/government multiplier. New-factory output receives current modifiers. China therefore gets its 20% bonus on expansion as well as the benefit already included in its initial capacity.
- Factories and the legacy industrial base have no specified energy upkeep; their productivity is not throttled by energy shortages. Research facilities, data centers, and drone facilities are throttled.
- Currency, energy, minerals, innovation, and military persist; compute and productivity are renewed annually. Starting compute is zero, so compute-consuming projects require a later production cycle.

### Shortage cascade

1. Mines add minerals, including Russia's resource modifier. Thermal plants demand 0.1 mineral each. Their operating ratio is `min(1, available minerals / demand)`; only the supplied fuel is consumed.
2. Thermal and renewable plants produce energy, including Russia's resource modifier. Energy consumers share the available stock and fresh production proportionally. The energy operating ratio is `min(1, available energy / demand)`.
3. Operational data centers produce `10 × count × energy ratio` compute. Cyber labs demand 5 compute each; research labs demand `5 × energy ratio` each. Apply any US compute discount to demand, then ration available compute proportionally.
4. Drones scale military output by energy supply; cyber labs scale it by compute supply. Research-lab innovation scales by both energy and compute supply. Resource stocks never become negative.
5. New military production increases both current power and military capacity. If any reserve exists after production, recover up to **1% of military capacity**, capped at missing strength. Recovery restores current power only; it does not expand capacity or deploy troops.

Currency maintenance remains payable even when resource shortages suspend operation. Shortage reports show production, consumption, and operating ratios.

## 6. Finance and debt

Tax revenue is `GDP × tax rate`. Taxes can range from 0% to 75%. Taxes use GDP after any completed infrastructure investment, before annual GDP growth.

Annual income comprises taxes, dominance bonuses, private-trade revenue, tariffs, EU luxury exports, and received foreign interest. Expenses comprise domestic/foreign interest, facility maintenance, and **0.005 T per deployed military point**. Reserves have no military currency upkeep. Military upkeep uses deployments after orders and before combat.

Operating deficits consume existing treasury first. **Only an uncovered shortfall issues new domestic debt**, leaving treasury at zero. This preserves the original debt rule over the summary's unconditional deficit borrowing. Discretionary construction, outreach, aid, and principal repayment must fit current reserves; they cannot borrow automatically or use future income.

The cash ledger must reconcile opening treasury, planned spending, received principal/aid, all operating receipts/costs, new borrowing, and closing treasury. Foreign interest, foreign principal, and aid are actual transfers: the amount deducted from one faction is credited to the other.

### Domestic debt

Domestic interest is `5% + (100 − content)/1000`, from the summary. Thus content 60 means 9%. Use current content at the economic update, before the new year's content settlement. Domestic interest goes to the domestic economy, not a foreign government. Domestic principal can be repaid in any planning phase.

### Foreign debt contracts

The original's domestic/foreign splits, creditor weights, and fixed-term contract mechanic take precedence over the summary's single dynamic rate on all debt.

- Initial foreign interest: **4%**. Default term: **three years**. Rates are locked until maturity.
- Initial renewals open in round 3, then rounds 6, 9, etc. under default terms. A rate selected at maturity applies to that resolution's interest payment.
- The lender chooses the renewal rate, between 0% and 20%. The borrower can repay some or all principal at maturity. Unpaid principal rolls into a new fixed-term contract; there is no principal payment if the borrower chooses not to repay.
- Increasing the rate by one percentage point reduces the bilateral relationship by 0.05; reducing it improves the relationship equivalently. The effect applies only while principal remains outstanding.
- A faction cannot own its own foreign debt. For each borrower, normalize the other three creditors' 30/41/24/5 weights to sum to 100%. This conserves each stated foreign-debt total. The weights are relative lender weights, not exact aggregate ownership percentages.
- Fully repaid contracts produce no interest. New operating deficits create domestic debt, not automatically funded foreign contracts.

### Dominance revenue

A faction's military share on a front is `its deployed power / all deployed power`. An empty front gives everyone zero share. Russian damage resistance does not inflate this ownership share. Allied forces do not count twice for tax purposes.

| Own military share | Bonus to base tax revenue from that front |
|---|---:|
| Less than 25% | 0% |
| At least 25%, below 50% | 5% |
| At least 50%, below 75% | 10% |
| At least 75% | 15% |

Take one tier per front and add across all four fronts, for a maximum 60% bonus. Calculate after deployment orders and before combat, consistent with the economic update preceding military resolution. A front can grant a tax bonus while contested. **Military share and territorial influence are different metrics.**

## 7. Diplomacy and trade

Trade and military alliances require matching offers from both parties. Either partner can end an active agreement by withdrawing its offer. An unaccepted offer persists into future rounds. Trade, tariffs, and military disputes can coexist.

Relationships stay symmetric and are clamped to 1–5. Each year, sum these effects:

- General hostility drift: −0.02.
- Active trade agreement: +0.08.
- Tariffs: `−0.3 × (both tariff fractions added together)`.
- Diplomatic outreach: +0.2 per actor, costing 0.1 T per target per year. US outreach is +0.22.
- Foreign aid: transfer **1 T** and add **0.25** relationship; a US grant adds 0.275. This converts the summary's +5 on a 0–100 scale to the original scale. One grant per recipient per year is allowed.
- Each opposed faction pair on a contested front: −0.15 per front.
- Contract-renewal effects described above.

Tariffs range from 0% to 50%. Let `openness = (1 − own tariff) × (1 − partner tariff)`.

- With an agreement, each government receives `min(own GDP, partner GDP) × 1.5% × openness` as private-trade revenue.
- Tariff revenue is `partner GDP × 1.5% × own tariff × openness`, multiplied by 0.25 without an agreement.
- Private-trade, tariff, and luxury-export revenue is newly generated income from the modeled private economy; it is not a direct withdrawal from another government's treasury.
- Aid transfers money; outreach pays for diplomatic activity. They are separate actions and can both be selected.

The trade-revenue formulas, outreach, relationship increments, and annual drift are explicit balance defaults for unspecified original mechanics. Shared national benefits are defined in section 4.

## 8. Fronts, combat, and territorial influence

The four fronts are **Eastern Europe**, **Pacific & South China Sea**, **Arctic**, and **South America**. Deployed units persist until reassigned or destroyed; new and recovered military remains in reserve. Total deployments cannot exceed current military power.

Connected allies **present on the same front** form a coalition. An absent intermediary does not connect two otherwise unallied forces. Coalitions combine strength and do not attack their own members. This combined treatment applies to combat; only the EU's explicitly coalition-based objective also counts allied troop shares.

### Simultaneous attrition

For each coalition on a contested front:

`raw loss = max(0, 0.01 × own coalition strength + 0.10 × (strongest opposing coalition strength − own coalition strength))`

If the coalition includes Russia, multiply loss by 0.9. Cap loss at the coalition's deployed strength and divide it between members in proportion to their deployments. All coalitions use the same pre-combat snapshot. Losses reduce both deployed and total current power, but not military capacity.

This uses the summary's decay equation, adapted to the original's military alliances and Russian damage-resistance trait. A sufficiently stronger coalition can take no losses. Uncontested fronts have no combat attrition. Each faction involved in contested combat still incurs the relationship/content effects even if its numerical losses are zero.

### Influence and recovery of control

Each front has 100 territorial-influence capacity. If exactly one coalition survives, it gains **10 influence per year**, divided by surviving troop shares. First fill unclaimed influence; when that is exhausted, displace rival influence proportionally. Influence cannot exceed 100 in total. A fully controlled front does not generate extra points beyond that cap.

If multiple coalitions survive, nobody gains influence. If all forces are destroyed, nobody gains influence. Previously established influence persists after withdrawal.

This recoverable 0–100 territorial-control model replaces the summary's monotonically accumulating sphere score, as agreed when fixing EU victory. Its 10-point annual gain is a configurable balance default for that revised scale. It prevents a single early Russian score from making EU victory permanently impossible.

## 9. Citizens, innovation, and growth

Initial content is taken from the faction table. Subsequent annual settlement uses the summary's tax/mobilization/mine formula, extended to preserve the original innovation/GDP benefits and government-transition mechanics.

Before clamping, compute:

`negative = 50 × tax fraction + 0.003 × deployed military + mines + 1.5 × contested fronts + negative government adjustment + transition unrest + shortage penalty`

`positive = min(10, innovation × 0.1) + persistent civic support + positive government adjustment`

`content = 100 − negative × discontent multiplier + positive`

The discontent multiplier is 0.9 for the US and 1 elsewhere. Mobilized military is sampled before combat, so units lost that year still count. Transition unrest is 5 while transitioning. Shortage penalty is `4 × (1 − lowest energy/compute/thermal-fuel operating ratio)`. Clamp content to 0–100, then add the positive GDP-growth benefit below, again capped at 100.

Annual GDP growth uses content before this annual settlement and innovation after production:

`growth = 0.01 + (prior content − 50) × 0.0003 + innovation × 0.0001 − max(0, tax fraction − 0.30) × 0.04 − contested fronts × 0.003 − energy shortfall × 0.02`

Clamp growth to −5% through +5%, then multiply GDP by `1 + growth`. Positive growth adds `growth × 10` content. Tax revenue was already assessed on pre-growth GDP. These coefficients fill the original's unspecified growth and innovation/content effects.

Public-service projects accumulate civic support. Research-program, infrastructure, and modernization projects affect their corresponding stocks immediately on completion. Mine penalties are included permanently in the annual content formula rather than repeatedly subtracting from the prior year's content.

## 10. Strategic objectives and victory

Default mode checks each faction's entire condition set **after combat and society settle**. All conditions must hold for **three consecutive completed rounds**. The initial map never counts as a completed round. Missing even one condition resets that faction's streak to zero.

### European Union — European security and Arctic balance

1. The **EU security coalition holds at least 60% military share in Eastern Europe**. The EU must have its own forces deployed there. Connected allies present on that front count, but a coalition containing Russia cannot satisfy this condition.
2. **Russian current territorial influence in Eastern Europe is at most 10/100.** This is a recoverable current value, not a lifetime score.
3. **No other faction holds more than 40% military share in the Arctic.** Other factions include allies. An empty Arctic counts as neutral.

At the default start, EU military share in Eastern Europe is `60/140 = 42.86%`; there is no alliance; Russian influence is 45. Both eastern conditions fail. The largest foreign Arctic share is the US's `60/160 = 37.5%`, so Arctic balance currently holds. The EU therefore starts with **one of three conditions met and a zero-year streak**.

### United States — Monroe doctrine and Arctic dominance

1. Zero foreign military presence in South America, including allied foreign forces. An empty theater satisfies this condition.
2. At least **80% US military share in the Arctic**.
3. Chinese military share in the Pacific is **at most 50%**. An empty Pacific satisfies this ceiling.

The initial Chinese/Russian South American deployments and contested Arctic prevent an opening victory.

### China — Pacific and Arctic dominance

1. **More than 80% Chinese military share in the Pacific**; exactly 80% is insufficient.
2. At least **80% Chinese military share in the Arctic**.

### Russia — Eurasian and Arctic dominance

1. At least **99% Russian military share in Eastern Europe**.
2. At least **50% Russian military share in the Arctic**.

For US, China, and Russia, these dominance thresholds use **that faction's own forces**, not its coalition. Empty fronts never satisfy a positive dominance threshold. Russia's combat trait does not inflate objective percentages.

If multiple factions complete their required streak in the same resolution, declare all of them co-winners. Never choose a winner by processing order. Once recorded, a victory remains recorded even if control later changes. The player may continue the world or start a new campaign.

Alternative modes:

- **Open-ended:** track objectives and streaks but never declare a winner.
- **Total influence:** default target 250 out of 400; a faction at or above the target wins if it has the highest total. Equal leaders qualify together. This mode does not require a three-year streak. Faction objectives remain visible for reference.

## 11. Computer opponents

Computer factions obey the same budgets, treaties, contracts, supply chains, combat, and victory checks as humans. They receive no extra resources or free constructions.

They commit approximately **80%** of current military, retaining the rest as reserves. Deployments use reproducible ±10% variation around these objective-oriented weights, normalized to the committed total:

| Faction | Eastern Europe | Pacific | Arctic | South America |
|---|---:|---:|---:|---:|
| EU | 65% | 0% | 35% | 0% |
| US | 10% | 25% | 45% | 20% |
| China | 0% | 55% | 45% | 0% |
| Russia | 60% | 0% | 40% | 0% |

This refines the summary's unrestricted random distribution so computer deployments relate to their objectives. The default variation seed is 17. Identical state, seed, and orders produce identical outcomes; reloading a save does not reroll a battle.

Other policies are explicit first-iteration defaults:

- Offer trade at relationship ≥2.6 unless the previous own tariff was ≥50%; offer alliances at ≥3.7; share transferable benefits with trading partners at ≥3.0.
- Tariffs are 25% below relation 2.2, 10% below 3, and zero otherwise.
- On renewal, charge 3% at relation ≥3.5, 6% below 2.5, and 4% otherwise.
- Adjust taxes upward when cash is below 1 T and debt exceeds GDP, or downward for content below 40. AI tax policy stays within 15–50%.
- Pay for outreach to the closest partner when reserves/content allow and the relationship is below 4.7.
- Prioritize power/compute shortages, low minerals, and low content. Otherwise rotate among industry, research, infrastructure, military, and services. Preserve a small treasury reserve and use the same affordability checks as human plans.
- Bound investment planning to 40 allocation attempts per faction per year; unused productivity expires.

## 12. Interface and persistence requirements

- A short introduction explaining annual planning, truthful forecasts and the three-year default objective hold, with a default EU quick start, scenario selection and portable-save import. Existing local campaigns resume directly.
- Faction/mode selection, visible starting assets and deployments, and adjustable scenario settings.
- A situation room with the world map, key metrics, world comparison, infrastructure comparison, and recent developments.
- Construction controls showing startup resource costs, available productivity, completed facilities, saved work, expected completions and partial work after End year, remaining productivity needed in later years, paused work, and last year's completions. Forecasts follow actual construction resolution, including bulk units, projects, and treaty discounts; invalid drafts clear expected values. Distinguish drafts from saved progress and explain that unfinished work needs a fresh annual allocation.
- Diplomacy controls for tariffs, offers, shared benefits, outreach, and aid.
- A military view separating deployed power, reserves, military shares, territorial influence, and economic bonuses.
- Government/finance controls with locked contract terms, maturity dates, principal repayments, and a reconcilable cash ledger.
- Objectives with condition-by-condition status, consecutive-year counters, rival progress, and a clear victory result.
- Objective planning compares the resolved world with the exact post-combat forecast, including numerical gaps, hold resets, and coalition blockers. A percentage-point gap is not a suggested troop allocation. Each condition links to its theater. The victory watch uses the selected objective, influence, or open-ended rules; an already declared victory remains permanent.
- Before commitment, surface predicted shortages, operating deficits, automatic borrowing, expiring productivity, and imminent victory. Invalid drafts clear predictions. Shared-player forecasts remain conditional on the current drafts.
- Production/shortage reports, historical charts, and a year-by-year chronicle.
- A live resource forecast reflecting current choices: current stock/capacity, values after orders and transfers, annual system change, expected next-year values, and net changes. Include currency, energy, minerals, compute, productivity, innovation, military, GDP, content, and debt, plus the projected cash ledger and shortages. Use the same rules as actual resolution without changing state. Solo forecasts include reproducible projected computer responses; hotseat/sandbox forecasts use current drafts and identify that other players may change them. Explicitly distinguish renewed compute/productivity capacity from accumulated stocks. Invalid drafts show an explanation instead of a stale or misleading forecast.
- A rulebook showing this authoritative design and the active scenario settings.
- Editable drafts, explicit end-year control, hotseat handoffs, and portable saves containing the world, current plans, commitments, settings, objective streaks, and winners.
- An interactive command map for all four fronts, selectable by pointer, keyboard or a native theater selector. Compare current deployments and influence, draft coalition strength and own military share, planned upkeep, projected survivors/influence, and the relevant objective conditions. All projections use the same engine and computer responses as resolution.
- Each map theater has separate current troop-share and territorial-influence bars. Troop shares divide the forces actually present; influence uses a fixed 100-point scale with unclaimed territory shown separately. A neutral marker avoids implying that an influence leader also leads the military. Numeric descriptions supplement faction colors. Narrow screens pan the map horizontally to retain readable theater cards.
- A planning ledger on every command screen, fixed during desktop scrolling, with current resources, order/transfer changes, annual changes and expected end values. Show remaining productivity, invalid drafts and changes from standing orders. Undo is per faction for the current year/session, bounded to 50 edits. Reset restores standing orders and is undoable; committed hotseat orders remain locked until explicitly reopened. No forecast values are displayed for invalid drafts.
- One remembered draft alternative per faction for the current year/session. Compare expected resources, military shares, territorial influence and objective hold using the same current world and rival drafts for both alternatives. In solo, each alternative gets its actual reproducible computer response. Restoring the alternative is undoable; committed drafts cannot be replaced. Remembered alternatives are temporary and do not enter portable saves or automatic recovery.
- Optional synthesized cues for applied edits, invalid drafts, commitments and results, with a test control, mute and 0–100% volume. No essential information is audio-only. Sound defaults off; cues do not repeat on navigation or queue while muted. Text scales of 100%, 115%, 130% and 150% and a reduced-motion preference recover with the local campaign, separately from gameplay saves. Reduced motion defaults on and respects the system preference. At 130% or larger, summary actions use a separate row and the ledger scrolls with the page.
- Optional, skippable first-three-year guidance suggests an investment, diplomatic choice, deployment comparison, resource forecast and objective check. Alternative choices remain available. Guidance uses actual drafts and results and never modifies assets, victory conditions or objective streaks.
- Instant, manually advanced turn review in actual engine phase order: treaties/orders, economy/shortages, relations, combat/influence, society, and objectives. Combat and influence remain grouped because each theater resolves its losses and then any influence gain before the next theater. Headline selection ranks objective-hold changes, shortages, borrowing and relative resource/military/society changes; headlines link to their recorded phase. Skip/replay does not advance the simulation. Legacy ungrouped reports remain readable without inventing missing phase data.
- Automatic local recovery of resolved state, applied draft edits (including excessive allocations), hotseat commitments/handoff, and presentation preferences. Replace checkpoints atomically and retain the previous validated copy. A corrupt current file falls back to that copy; unrecoverable corruption leaves manual import/new-campaign options. Report write failures without losing the live session. Detect stale sessions before overwriting a newer checkpoint. Manual portable saves remain supported independently. There is one recovery slot per local server installation; separate campaigns can be exported, and separate servers need separate recovery directories.

Current state must survive a save/load cycle without rerolling outcomes. Keep up to 250 annual snapshots and 100 detailed reports; current assets and orders are retained regardless of history trimming.

The current gameplay rules identifier is `1`; the portable save schema is `3`. These interface and diagnostic updates change report/presentation/persistence structure, not numerical rules, starting assets, opponent policies or victory decisions. The campaign evaluation harness is separate from playable computer policy: it applies ordinary orders and records actual results; its observation window adds no game turn cap. Version 2 saves retain their prior reports; version 1 follows the established prototype migration. Future unknown gameplay rules identifiers must be rejected until a compatibility path is defined. Autosave and the interface's portable importer may restore structurally valid overallocated drafts; they remain invalid for forecasts/resolution and cannot be restored as committed hotseat orders.

## 13. Reconciliation and additions register

The following decisions resolve conflicting or incomplete source material:

| Topic | Authoritative resolution |
|---|---|
| China tax; creditor weights; government starts; national traits | Original document |
| Treasury except EU; starting resources/content/innovation/productivity | Supplemental summary |
| Foreign interest and debt shortfalls | Original fixed-term contracts and treasury-first borrowing |
| Factory costs/output; data-center cost and one-time innovation; domestic-rate formula | Supplemental summary |
| Drone innovation effect; shared national benefits; alliances; government transitions | Original mechanics, with the explicit missing coefficients above |
| Military attrition | Summary's decay equation applied to allied coalitions, retaining original Russian damage resistance |
| Tax bonuses on contested fronts | Summary's thresholds, confirmed by the user |
| Influence | User-confirmed uncontested gains; recoverable 100-point control for the revised EU objective |
| EU objectives, three-year hold, meaningful opening deployments | User-confirmed direction; exact scenario values and coalition semantics are specified above |
| Opening influence/facility counts; resource cost efficiency; research lab/projects; government modifiers; GDP/content extensions; trade formulas | Explicit implementation defaults filling source gaps |
| AI placement | Summary's 80% mobilization with objective-oriented, reproducible variation |

The map is schematic. Internal parties, live political data, resource import contracts, population, inflation, exchange rates, nuclear warfare, tactical units, network multiplayer, and event cards are outside this iteration. Government labels and numeric modifiers describe the game scenario rather than empirical political claims.

## 14. Principles for further development

The central player promise is to **understand the consequences of an order, commit to a strategy, and hold a geopolitical advantage under pressure**. Further development should make those choices easier to read and more satisfying to execute while preserving the mechanics specified above.

- Retain four asymmetric factions, simultaneous annual resolution, local hotseat, and the separate roles of economic strength, military presence, and territorial influence.
- Treat the live forecast as part of the core experience. Solo forecasts reflect the same reproducible opponent response used at resolution; shared-player forecasts remain conditional on the currently visible drafts. Do not introduce hidden randomness or silently weaken forecast accuracy.
- Keep military share, territorial influence, annual resource flows, stored resources, and renewed capacities visibly distinct. Improvements to map interaction or presentation must preserve those meanings.
- Derive briefings and turn summaries from the actual resolved world. A dramatic presentation must explain real consequences, including setbacks and costs.
- Preserve editable planning and portable campaign state as presentation improves. Atomic local recovery and draft undo are implemented as described above; additional persistence/distribution features remain in the development roadmap until implemented.
- Assess faction balance and campaign pacing with recorded playthroughs. The current defaults are a documented starting point, not evidence that every faction or strategy is already balanced.

Changes to numerical balance, opponent policies, starting scenarios, information visibility, or victory conditions must be recorded here with their rationale and corresponding verification. Distinguish a presentation improvement from a gameplay change. Preserve an identifiable rules version for affected campaigns and document any migration or compatibility limits. Roadmap ideas such as additional scenarios or difficulty policies require this reconciliation before becoming part of the game. Event-based policies remain deferred unless the user changes that decision.
