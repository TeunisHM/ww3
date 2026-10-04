extends RefCounted
## Screens render detached Python data and send explicit order edits.

const W = preload("res://scripts/desk_widgets.gd")
const Chart = preload("res://scripts/history_chart.gd")
const FRONT_POSITIONS = [Vector2(0.58, 0.32), Vector2(0.86, 0.56), Vector2(0.64, 0.12), Vector2(0.30, 0.72)]
var host
var rulebook := ""


func _init(controller) -> void:
	host = controller


func build(index: int, box: VBoxContainer) -> void:
	match index:
		0: situation(box)
		1: economy(box)
		2: diplomacy(box)
		3: military(box)
		4: government(box)
		5: objectives(box)
		6: chronicle(box)
		7: rule_reference(box)


func fold(parent: Node, caption: String, id: String, opened: bool = false) -> VBoxContainer:
	var section := W.column(parent)
	var toggle := W.button(section, caption, func(): pass)
	toggle.toggle_mode = true
	toggle.button_pressed = host.folds.get(id, opened)
	var content := W.column(section)
	content.visible = toggle.button_pressed
	toggle.toggled.connect(func(value: bool): content.visible = value; host.folds[id] = value)
	return content


func order_spin(parent: Node, caption: String, field: String, key: String, value: float, maximum: float, step: float = 1.0, scale: float = 1.0, eligible: bool = true) -> SpinBox:
	var spin := W.spin(parent, caption, value, maximum, step)
	host.register_edit(spin, field + "/" + key, eligible)
	spin.value_changed.connect(host._order_changed.bind(field, key, scale))
	return spin


func outlook() -> String:
	var view: Dictionary = host.view
	var game: Dictionary = view.game
	var faction: String = host.commander
	var lines := PackedStringArray()
	if not game.winners.is_empty():
		lines.append("Victory secured: %s. You can keep playing." % " + ".join(game.winners))
	if view.forecast != null:
		for item in view.desk.victory:
			if item.faction == faction:
				if game.rules.victory_mode == "influence":
					lines.append("Influence: %s → %s / %s" % [W.number(item.current, 1), W.number(item.expected, 1), W.number(item.target, 1)])
				else:
					lines.append("Objectives: %d/%d expected conditions · hold %d → %d / %d years%s" % [int(item.conditions_expected), int(item.condition_count), int(item.current), int(item.expected), int(item.target), " (reference in open mode)" if game.rules.victory_mode == "open" else ""])
				if game.rules.victory_mode != "influence" and item.current > 0 and item.expected == 0:
					lines.append("Warning: this draft is expected to reset your objective hold.")
			if item.wins_this_year:
				lines.append("Expected victory this year: " + str(item.faction))
	for alert in view.desk.factions[faction].alerts:
		if alert[0] == "warning":
			lines.append(alert[1])
	return "\n".join(lines)


func situation(box: VBoxContainer) -> void:
	var view: Dictionary = host.view
	var faction: String = host.commander
	var nation: Dictionary = view.game.nations[faction]
	W.text(box, view.catalog.scenario[faction].name + " · " + nation.government)
	W.prose(box, view.catalog.scenario[faction].brief + "\n" + "\n".join(view.catalog.traits[faction]))
	_map(box)
	_theater(box, false)
	var stats: Array = []
	var prior: Dictionary = view.game.history[-2].nations[faction] if view.game.history.size() > 1 else {}
	for key in ["gdp", "currency", "content", "military", "influence"]:
		var value: float = view.desk.factions[faction].influence if key == "influence" else nation[key]
		stats.append([key.capitalize(), W.number(value), W.number(value - float(prior[key])) if prior.has(key) else "—"])
	W.table(box, ["National position", "Now", "Change last year"], stats)
	var rows: Array = []
	for other in view.factions:
		var n: Dictionary = view.game.nations[other]
		var facts: Dictionary = view.desk.factions[other]
		rows.append([other, W.number(n.gdp), W.number(facts.debt), W.number(n.content, 1), W.number(n.military, 1), W.number(facts.influence, 1)])
	W.table(box, ["Faction", "GDP · T", "Debt · T", "Content", "Military", "Influence"], rows)
	var infrastructure := fold(box, "Infrastructure comparison", "infrastructure")
	rows = []
	for key in view.catalog.investments:
		if view.catalog.investments[key].kind == "building":
			var row: Array = [view.catalog.investments[key].name]
			for other in view.factions:
				row.append(int(view.game.nations[other].buildings[key]))
			rows.append(row)
	W.table(infrastructure, ["Facility", "EU", "US", "China", "Russia"], rows)
	var brief := W.section(box, "Command briefing")
	if nation.transition_target != null:
		W.text(brief, "Government transition: %d years remaining. Annual civil unrest applies." % int(nation.transition_remaining))
	if float(nation.last_ledger.get("new_borrowing", 0)) > 0:
		W.text(brief, "Last year's budget required borrowing. Review taxes and upkeep in Government.")
	if not view.game.reports.is_empty():
		for item in view.desk.review.highlights[faction]:
			W.prose(brief, item.message)
	else:
		W.text(brief, "Allocate productivity in Economy, then compare deployments in Military. Nothing advances until you end the year.")
	guidance(box)


func _map(box: VBoxContainer) -> void:
	var map := TextureRect.new()
	map.texture = preload("res://assets/world.svg")
	map.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	map.stretch_mode = TextureRect.STRETCH_SCALE
	map.custom_minimum_size = Vector2(600, 290)
	box.add_child(map)
	for index in range(4):
		var marker := Button.new()
		marker.text = ["Europe", "Pacific", "Arctic", "South America"][index]
		marker.anchor_left = FRONT_POSITIONS[index].x
		marker.anchor_top = FRONT_POSITIONS[index].y
		marker.offset_left = -65
		marker.offset_right = 65
		marker.offset_bottom = 36
		marker.tooltip_text = host.view.fronts[index]
		marker.modulate = Color("71d6bc") if host.view.fronts[index] == host.selected_front else Color.WHITE
		marker.pressed.connect(host._select_front.bind(index))
		map.add_child(marker)
		host.markers.append(marker)
	W.text(box, "Schematic fronts, shared information. Select a theater with click or Tab + Enter. Troop share and territorial influence are separate measures.")
	var legend := W.row(box)
	for faction in host.view.factions:
		W.text(legend, faction).modulate = Color(host.view.catalog.colors[faction])
	for front in host.view.fronts:
		var row := W.section(box, front)
		_bars(row, "Troop share now", host.view.desk.fronts[front].factions, "share", 100.0)
		_bars(row, "Territorial influence / 100", host.view.desk.fronts[front].factions, "influence", 1.0)


func _bars(parent: Node, caption: String, data: Dictionary, key: String, scale: float) -> void:
	var line := W.row(parent)
	var label := W.text(line, caption)
	label.custom_minimum_size.x = 200
	label.size_flags_horizontal = Control.SIZE_FILL
	var bars := W.row(line)
	bars.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bars.add_theme_constant_override("separation", 0)
	var used := 0.0
	for faction in data:
		var value := float(data[faction][key]) * scale
		used += value
		if value <= 0:
			continue
		var bar := ColorRect.new()
		bar.color = Color(host.view.catalog.colors[faction])
		bar.custom_minimum_size.y = 18
		bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		bar.size_flags_stretch_ratio = value
		bar.tooltip_text = "%s · %.2f%%" % [faction, value]
		bars.add_child(bar)
	if used < 100:
		var unused := ColorRect.new()
		unused.color = Color("334350")
		unused.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		unused.size_flags_stretch_ratio = maxf(.001, 100 - used)
		unused.tooltip_text = "Unclaimed / no forces: %.2f%%" % (100 - used)
		bars.add_child(unused)


func _theater(box: VBoxContainer, full: bool) -> void:
	var view: Dictionary = host.view
	var front: String = host.selected_front
	var current: Dictionary = view.desk.fronts[front]
	var section := W.section(box, front + " · theater briefing")
	var selector := W.choice(section, "Inspect theater", view.fronts, front)
	selector.item_selected.connect(host._select_front)
	var detail := "Current: " + str(current.status)
	var rows: Array = []
	for faction in view.factions:
		var now: Dictionary = current.factions[faction]
		var after: Dictionary = view.forecast.fronts[front].expected.factions[faction] if view.forecast != null else {}
		rows.append([faction, W.number(now.deployed, 1), "%.1f%%" % (float(now.share) * 100), W.number(now.influence, 1), W.number(after.get("deployed"), 1), W.number(float(after.share) * 100, 1) + "%" if after.has("share") else "—", W.number(after.get("influence"), 1)])
	W.table(section, ["Faction", "Troops now", "Share now", "Influence now", "Survivors", "Share after", "Influence after"], rows)
	for group in current.coalitions:
		detail += "\nCurrent coalition: %s · %.2f power" % [" + ".join(group.members), float(group.strength)]
	if view.forecast != null:
		for stage in ["planned", "expected"]:
			for group in view.forecast.fronts[front][stage].coalitions:
				detail += "\n%s coalition: %s · %.2f power" % [stage.capitalize(), " + ".join(group.members), float(group.strength)]
		if full:
			rows = []
			for faction in view.factions:
				var plan: Dictionary = view.forecast.fronts[front].planned.factions[faction]
				var after: Dictionary = view.forecast.fronts[front].expected.factions[faction]
				rows.append([faction, W.number(plan.deployed), "%.2f%%" % (float(plan.share) * 100), W.number(plan.upkeep, 4), W.number(after.upkeep, 4)])
			W.table(section, ["Faction", "Planned forces", "Planned share", "Upkeep · T", "Survivor upkeep"], rows)
	else:
		detail += "\nForecast unavailable until all required drafts are valid."
	host.front_detail = W.prose(section, detail)
	for faction in view.factions:
		for item in view.desk.factions[faction].objectives:
			if item.current.front == front:
				W.text(section, "%s: %s\nNow: %s · After combat: %s" % [faction, item.current.condition, item.current.current, item.expected.current if item.expected != null else "—"])


func economy(box: VBoxContainer) -> void:
	var view: Dictionary = host.view
	var faction: String = host.commander
	var nation: Dictionary = view.game.nations[faction]
	var facts: Dictionary = view.desk.factions[faction]
	W.text(box, "Plan now → Build & produce at End year → Spend or deploy next turn")
	W.prose(box, "Allocate productivity as work, not a building count. Completed facilities produce and pay upkeep in that same annual update; shortages can limit output. Unfinished work is already paid for and carries forward, but needs another allocation to finish. Unallocated productivity expires. Investments resolve in the catalog order below.")
	var summary: Array = []
	for item in facts.construction:
		summary.append([item.name, W.number(item.current_count, 0), "%.1f%%" % (float(item.current_progress) * 100), W.number(item.allocated_work, 1), W.number(item.completed, 0), W.number(float(item.expected_progress) * 100, 1) + "%" if item.expected_progress != null else "—"])
	W.table(box, ["Construction status", "Built now", "Saved work", "Allocated", "Completions", "Saved after"], summary)
	W.text(box, "Remaining productivity: %.2f" % float(facts.remaining_productivity))
	for item in facts.construction:
		var key: String = item.key
		var spec: Dictionary = view.catalog.investments[key]
		var cost: Dictionary = facts.costs[key]
		var section := W.section(box, spec.name + (" · repeatable project" if spec.kind == "project" else " · %d completed" % int(item.current_count)))
		W.text(section, spec.description)
		W.text(section, "Startup per new unit: %.3f T · %.2f minerals · %.2f compute · %.2f energy. Work: %.1f productivity." % [float(cost.currency), float(cost.minerals), float(cost.compute), float(cost.energy), float(cost.productivity)])
		var spin := order_spin(section, "Productivity allocation", "investments", key, float(item.allocated_work), float(nation.productivity), .1)
		host.investments[key] = spin
		if key == "factory":
			host.factory = spin
		var progress := ProgressBar.new()
		progress.value = float(item.current_progress) * 100
		progress.tooltip_text = "Carried work already paid for; new startup resources are not charged twice."
		section.add_child(progress)
		W.text(section, "Saved work: %.1f%% · %.2f productivity to finish current/next unit.%s" % [float(item.current_progress) * 100, float(item.remaining_work), " Paused until work is allocated." if float(item.current_progress) > 0 and float(item.allocated_work) == 0 else ""])
		if item.forecast_valid:
			W.text(section, "Expected: %d completion(s), %d new unit(s) started; %.1f%% unfinished, %.2f work left. Forecast work per unit: %.2f." % [int(item.completed), int(item.started), float(item.expected_progress) * 100, float(item.expected_remaining_work), float(item.work_per_unit)])
		else:
			W.text(section, "Expected construction is unavailable while a draft is invalid.")
	W.text(box, "Current prices include active trade. The forecast also includes matching new agreements and their discounts. Every new unit pays its full startup cost, even if only partly completed.")
	if not view.game.reports.is_empty():
		var completions := PackedStringArray()
		for message in view.game.reports[-1].messages:
			if str(message).begins_with(faction + " completed "):
				completions.append(message)
		W.prose(box, "Last completions: " + ("\n".join(completions) if not completions.is_empty() else "None last year."))
	var costs := fold(box, "Production & operating costs", "production")
	W.entries(costs, nation.last_production, "Last production")
	var rows: Array = []
	for spec in view.catalog.investments.values():
		if spec.kind == "building":
			rows.append([spec.name, spec.currency_upkeep, spec.energy_upkeep, spec.compute_upkeep, spec.mineral_upkeep])
	W.table(costs, ["Facility upkeep", "Currency · T", "Energy", "Compute", "Minerals"], rows)
	W.button(box, "Inspect full resource forecast", host.show_planning)


func diplomacy(box: VBoxContainer) -> void:
	var view: Dictionary = host.view
	var faction: String = host.commander
	var nation: Dictionary = view.game.nations[faction]
	var order: Dictionary = view.game.orders[faction]
	W.text(box, "Trade and alliances need matching offers from both factions. Either partner may withdraw. Solo computer responses depend on relations.")
	for other in view.factions:
		if other == faction:
			continue
		var section := W.section(box, view.catalog.scenario[other].name)
		W.text(section, "Relationship %.3f / 5 · Their tariff on you: %.1f%%" % [float(nation.relations[other]), float(view.game.nations[other].tariffs[faction]) * 100])
		var tariff := order_spin(section, "Tariff · %", "tariffs", other, float(order.tariffs.get(other, 0)) * 100, 50, .1, 100)
		host.diplomacy_controls["tariffs/" + str(other)] = tariff
		var fields := {"trade_offers": "Offer / maintain trade", "alliance_offers": "Offer / maintain alliance", "share_bonus": "Share my national trade benefit", "improve_relations": "Diplomatic outreach · %.2f T" % float(view.game.rules.diplomacy_cost), "foreign_aid": "Foreign aid · %.2f T" % float(view.game.rules.foreign_aid_amount)}
		for field in fields:
			if field == "share_bonus" and faction not in ["US", "China"]:
				continue
			var check := CheckBox.new()
			check.text = fields[field]
			check.button_pressed = other in order[field]
			section.add_child(check)
			host.register_edit(check, field + "/" + str(other))
			host.diplomacy_controls[field + "/" + str(other)] = check
			check.toggled.connect(host._list_changed.bind(field, other))
		var pair: Array = [faction, other]
		pair.sort()
		var key := "|".join(pair)
		var treaties := PackedStringArray()
		if key in view.game.trades:
			treaties.append("Trade")
		if key in view.game.alliances:
			treaties.append("Alliance")
		W.text(section, "Active: " + (" · ".join(treaties) if not treaties.is_empty() else "No agreements"))
		var pending := PackedStringArray()
		for field in ["trade_offers", "alliance_offers"]:
			if faction in view.game.orders[other][field]:
				pending.append(field.replace("_offers", ""))
		W.text(section, "Their recorded offers: " + (", ".join(pending) if not pending.is_empty() else "None"))
	W.prose(box, "EU trade shares a 25% data-center cost discount automatically. The US may share a 20% compute-consumption discount; China may share a 20% productivity increase. Bonuses do not stack with a faction's own copy.\nTariffs raise revenue but suppress trade and harm relations. Relationships deteriorate each year unless cooperation offsets the drift. Incoming foreign aid cannot fund orders in the same year.")


func military(box: VBoxContainer) -> void:
	var view: Dictionary = host.view
	var faction: String = host.commander
	var nation: Dictionary = view.game.nations[faction]
	var facts: Dictionary = view.desk.factions[faction]
	W.text(box, "Military %.2f · Capacity %.2f · Planned reserve %.2f · Influence %.2f / 400\nReserve recovery up to %.1f%% of capacity per year with reserves present. Current dominance tax bonus %.1f%%." % [float(nation.military), float(nation.military_capacity), float(facts.reserve), float(facts.influence), float(view.game.rules.reserve_recovery) * 100, float(facts.dominance_bonus) * 100])
	for front in view.fronts:
		host.deployments[front] = order_spin(box, front, "deployments", front, float(view.game.orders[faction].deployments[front]), float(nation.military), .1)
	W.text(box, "Reserves avoid combat. Deployments persist between years. An overcommitted plan blocks resolution; adjust it or undo.")
	_theater(box, true)
	var rules := fold(box, "How combat & influence work", "combat")
	W.prose(rules, "Coalition loss is max(0, %.1f%% of its strength + %.1f%% of the difference between the strongest opposing coalition and its own strength), capped at deployed strength. All losses use the same pre-combat snapshot and split in proportion to deployment. A coalition containing Russia takes 10%% less damage.\nConnected allies present on the same front form a coalition. A sole surviving coalition gains %.1f influence, split by surviving strength. Unclaimed influence fills first; then new control displaces rivals proportionally. Contested fronts gain no influence. Established influence survives withdrawal.\nOwn military shares of 25%%, 50%% and 75%% give tax bonuses of 5%%, 10%% and 15%% per front, using deployment after orders and before combat. Allied strength is not double-counted." % [float(view.game.rules.combat_base_decay) * 100, float(view.game.rules.combat_attrition) * 100, float(view.game.rules.influence_gain)])


func government(box: VBoxContainer) -> void:
	var view: Dictionary = host.view
	var faction: String = host.commander
	var nation: Dictionary = view.game.nations[faction]
	var order: Dictionary = view.game.orders[faction]
	var facts: Dictionary = view.desk.factions[faction]
	host.tax = order_spin(box, "Tax revenue as share of GDP · %", "tax_rate", "", float(order.tax_rate) * 100, 75, .1, 100)
	W.text(box, "At current GDP: %.3f T annually before other income and costs. Citizen content: %.1f / 100." % [float(nation.gdp) * float(order.tax_rate), float(nation.content)])
	host.government_choice = W.choice(box, "Government type", view.catalog.governments, order.government)
	host.register_edit(host.government_choice, "government", nation.transition_target == null)
	host.government_choice.item_selected.connect(host._government_changed)
	if nation.transition_target != null:
		W.text(box, "Transition to %s: %d years remaining. Annual unrest: %.1f content before national modifiers. Transitions cannot be redirected." % [nation.transition_target, int(nation.transition_remaining), float(view.game.rules.transition_unrest)])
	elif order.government != nation.government:
		W.text(box, "This begins a %d-year transition. Current government effects continue until completion." % int(view.game.rules.government_transition_years))
	var effect: Dictionary = view.catalog.government_effects[order.government]
	W.text(box, "Effects when active: ×%.2f productivity · ×%.2f innovation · %+.1f content." % [float(effect.productivity), float(effect.innovation), float(effect.content)])
	W.prose(box, "High taxes, conflict, shortages and transitions increase discontent. Innovation, GDP growth and public services can improve it. Lower content increases domestic interest rates.")
	var finance := W.section(box, "Public finances")
	W.text(finance, "Total debt %.4f T · Domestic principal %.4f T at %.2f%%" % [float(facts.debt), float(nation.domestic_debt), float(facts.domestic_interest) * 100])
	host.domestic_repayment = order_spin(finance, "Repay domestic principal · T", "domestic_repayment", "", float(order.domestic_repayment), float(nation.domestic_debt), .01)
	W.text(finance, "Recurring operating shortfalls become domestic debt. Construction and other discretionary orders must fit your current treasury.")
	if not nation.last_ledger.is_empty():
		W.entries(fold(finance, "Last year's complete cash ledger", "ledger"), nation.last_ledger, "Cash flow · T")
	W.text(box, "Foreign debt: lenders may change rates at maturity; borrowers may repay then. Unpaid principal renews for another fixed term. Higher renewal rates harm relations.")
	for contract in view.game.contracts:
		if faction not in [contract.borrower, contract.lender] or float(contract.principal) < 0.00000001:
			continue
		var mature: bool = view.game.round >= contract.matures_round
		var section := W.section(box, "%s owes %s · %.4f T · %.2f%%" % [contract.borrower, contract.lender, float(contract.principal), float(contract.rate) * 100])
		W.text(section, ("RENEWAL OPEN" if mature else "Locked until %d" % int(view.game.rules.start_year + contract.matures_round - 1)) + " · Annual interest transfer %.4f T" % (float(contract.principal) * float(contract.rate)))
		var control: SpinBox
		if faction == contract.lender:
			control = order_spin(section, "Renewal interest · %", "contract_rates", contract.id, float(order.contract_rates.get(contract.id, contract.rate)) * 100, 20, .25, 100, mature)
		else:
			control = order_spin(section, "Repay foreign principal · T", "foreign_repayments", contract.id, float(order.foreign_repayments.get(contract.id, 0)), float(contract.principal), .01, 1, mature)
		host.contract_controls[contract.id] = control


func objectives(box: VBoxContainer) -> void:
	var view: Dictionary = host.view
	var selected: String = host.inspect_faction
	var choice := W.choice(box, "Inspect faction objectives", view.factions, selected)
	choice.item_selected.connect(func(index: int): host.inspect_faction = view.factions[index]; host._render())
	W.text(box, view.catalog.objective_names[selected])
	W.text(box, "Victory mode: %s. Hold all conditions in the same post-combat check for %d consecutive years. Missing a condition resets the count." % [view.game.rules.victory_mode, int(view.game.rules.objective_hold_years)])
	var expected: Variant = view.forecast.streaks[selected] if view.forecast != null else null
	W.text(box, "Completed hold: %d / %d · Expected after combat: %s" % [int(view.game.objective_streaks[selected]), int(view.game.rules.objective_hold_years), W.number(expected, 0)])
	for item in view.desk.factions[selected].objectives:
		var section := W.section(box, item.current.condition)
		W.text(section, "Now · %s: %s\nAfter combat · %s: %s" % ["Met" if item.current.met else "Unmet", item.current.current, item.change, item.expected.current if item.expected != null else "Forecast unavailable"])
		W.text(section, item.current.detail)
		W.text(section, item.gap)
		if item.blocker != null:
			W.text(section, item.blocker)
		W.text(section, item.advice)
		W.button(section, "Inspect " + str(item.current.front), host.inspect_front.bind(item.current.front))
	W.text(box, "Gaps describe the resulting position, not a troop allocation. Military share and territorial influence are separate measurements.")
	var rows: Array = []
	for item in view.desk.victory:
		rows.append([item.faction, "%d/%d" % [int(item.conditions_now), int(item.condition_count)], "%s/%d" % [W.number(item.conditions_expected, 0), int(item.condition_count)], W.number(item.current, 1), W.number(item.expected, 1), W.number(item.target, 1), "Secured" if item.secured else "Wins this year" if item.wins_this_year else "Reference only" if view.game.rules.victory_mode == "open" else "Planning"])
	W.table(box, ["Victory watch", "Met now", "Expected", "Progress now", "Progress after", "Target", "Outlook"], rows)
	if view.game.rules.victory_mode == "open":
		W.text(box, "Open-ended mode tracks objectives for reference and never declares a winner.")
	elif view.game.rules.victory_mode == "influence":
		W.text(box, "The highest total influence wins once it reaches the target; tied leaders share victory. Objective holds are reference only.")


func chronicle(box: VBoxContainer) -> void:
	var view: Dictionary = host.view
	var metrics: Array = ["gdp", "currency", "debt", "content", "innovation", "military", "influence", "energy", "minerals"]
	var choice := W.choice(box, "Compare factions", metrics, host.history_metric)
	choice.item_selected.connect(func(index: int): host.history_metric = metrics[index]; host._render())
	var legend := W.row(box)
	for faction in view.factions:
		W.text(legend, faction).modulate = Color(view.catalog.colors[faction])
	var chart := Chart.new()
	chart.history = view.game.history
	chart.metric = host.history_metric
	chart.colors = view.catalog.colors
	box.add_child(chart)
	var rows: Array = []
	for item in view.game.history:
		var values: Array = [int(item.year)]
		for faction in view.factions:
			values.append(W.number(item.nations[faction][host.history_metric], 3))
		rows.append(values)
	W.table(fold(box, "Exact recorded values", "history_values"), ["Year", "EU", "US", "China", "Russia"], rows)
	if view.game.reports.is_empty():
		W.text(box, "End your first year to begin the chronicle.")
		return
	var selected: int = view.game.reports.size() - 1 if int(host.history_report) < 0 else mini(int(host.history_report), view.game.reports.size() - 1)
	var labels: Array = []
	for item in view.game.reports:
		labels.append("%d · Round %d · %d developments" % [int(item.year), int(item.round), item.messages.size()])
	var report_choice := W.choice(box, "Annual report", labels, labels[selected])
	report_choice.item_selected.connect(func(index: int): host.history_report = index; host._render())
	host.report = W.prose(box, "\n\n".join(view.game.reports[selected].messages))
	W.button(box, "Replay latest turn review", host.show_review)


func rule_reference(box: VBoxContainer) -> void:
	W.text(box, "The consolidated design defines rules, starting assets, objectives and configurable defaults.")
	W.button(box, "Export DESIGN.md", func(): host._export_design = true; host.save_dialog.current_file = "DESIGN.md"; host.save_dialog.popup_centered_ratio(0.75))
	if rulebook.is_empty():
		rulebook = host.design_text()
	var text := TextEdit.new()
	text.text = rulebook
	text.editable = false
	text.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
	text.custom_minimum_size.y = 480
	box.add_child(text)
	W.text(box, "Current campaign balance settings")
	var settings := TextEdit.new()
	settings.text = JSON.stringify(host.view.game.rules, "  ", false, true)
	settings.editable = false
	settings.custom_minimum_size.y = 320
	box.add_child(settings)


func guidance(box: VBoxContainer) -> void:
	if not host.ui.guide_enabled:
		return
	var view: Dictionary = host.view
	var faction: String = host.commander
	var section := fold(box, "First three years · guidance", "guide", view.game.round <= 3)
	if int(view.game.round) > 3:
		W.text(section, "The introduction is complete. Your campaign continues with the same objective rules. Guidance can be toggled in Settings.")
		return
	var step := int(view.game.round)
	W.text(section, "Year %d of 3 · Your orders stay yours" % step)
	W.prose(section, ["Try an investment, consider an agreement, and compare deployments against your objectives. Keeping a policy is also a choice.", "Review what the first orders achieved. Compare another investment with defending your weakest objective.", "Check whether the objective hold advanced or reset. All conditions must survive consecutive resolved years."][step - 1])
	for index in [1, 2, 3, 5]:
		W.button(section, view.catalog.pages[index], func(): host.tabs.current_tab = index)
	var order: Dictionary = view.game.orders[faction]
	var allocated := 0.0
	for value in order.investments.values():
		allocated += float(value)
	W.text(section, "Your draft: %.1f productivity invested · %d trade offers · %d alliance offers. Agreements need matching offers. Read the ledger before ending the year; it separates orders from annual production and upkeep." % [allocated, order.trade_offers.size(), order.alliance_offers.size()])


func planning(box: VBoxContainer) -> void:
	W.clear(box)
	var view: Dictionary = host.view
	var faction: String = host.commander
	var facts: Dictionary = view.desk.factions[faction]
	W.text(box, outlook())
	for alert in facts.alerts:
		W.text(box, alert[1])
	W.text(box, "Compute and productivity renew each year; unused capacity expires. Stocks carry forward. Forecasts include reproducible computer responses in solo and depend on all current drafts in shared play.")
	if facts.plan != null:
		W.text(box, "Own draft spending: %.4f T. Incoming aid cannot fund current orders." % float(facts.plan.spending))
	else:
		W.text(box, "Own draft invalid: " + str(facts.plan_error))
	if view.forecast != null:
		var data: Dictionary = view.forecast.factions[faction]
		var rows: Array = []
		for item in data.resources:
			rows.append([item.resource, W.number(item.current, 3), W.number(float(item.after_orders) - float(item.current), 3), W.number(item.after_orders, 3), W.number(item.system_change, 3), W.number(item.expected, 3), W.number(item.change, 3)])
		W.table(box, ["Resource", "Current", "Orders + transfers", "After orders", "Annual change", "Expected", "Net change"], rows)
		W.entries(fold(box, "Forecast complete cash ledger", "forecast_ledger"), data.ledger, "Cash flow · T")
		W.entries(fold(box, "Forecast production & shortages", "forecast_production"), data.production, "Production")
	else:
		W.text(box, "Forecast cleared: " + str(view.forecast_error))
	var changes := fold(box, "%d changed decisions" % facts.changes.size(), "changes", true)
	W.prose(changes, "\n".join(facts.changes) if not facts.changes.is_empty() else "No changes from standing orders. Reset restores policy and deployments to the resolved world; undo restores the previous edit.")
	var alternatives := W.section(box, "Compare draft alternatives")
	W.text(alternatives, "Remember this year's plan, try another, and compare both against the same current world and rival orders. Restoring is undoable. Alternatives last for this year and open session.")
	var actions := W.row(alternatives)
	host.remember_button = W.button(actions, "Remember this draft", func(): host._draft_command("remember"))
	host.restore_button = W.button(actions, "Restore remembered", func(): host._draft_command("restore"))
	host.compare_button = W.button(actions, "Refresh comparison", func(): host._draft_command("compare"))
	if host.comparison.is_empty():
		W.text(alternatives, "Remember a draft, then refresh the comparison after edits.")
		return
	for key in ["current", "remembered"]:
		if host.comparison[key].error != null:
			W.text(alternatives, key.capitalize() + " draft forecast unavailable: " + str(host.comparison[key].error))
	var current: Variant = host.comparison.current.forecast
	var remembered: Variant = host.comparison.remembered.forecast
	if current == null or remembered == null:
		return
	var rows: Array = []
	for index in range(current.factions[faction].resources.size()):
		var a: Dictionary = current.factions[faction].resources[index]
		var b: Dictionary = remembered.factions[faction].resources[index]
		rows.append([a.resource, W.number(a.expected, 3), W.number(b.expected, 3), W.number(float(a.expected) - float(b.expected), 3)])
	W.table(alternatives, ["Resource", "This draft", "Remembered", "Difference"], rows)
	rows = []
	for front in view.fronts:
		var a: Dictionary = current.fronts[front].expected.factions[faction]
		var b: Dictionary = remembered.fronts[front].expected.factions[faction]
		rows.append([front, "%.2f%%" % (float(a.share) * 100), "%.2f%%" % (float(b.share) * 100), W.number(a.influence), W.number(b.influence)])
	W.table(alternatives, ["Theater", "This share", "Remembered share", "This influence", "Remembered influence"], rows)
	W.text(alternatives, "Expected hold: this draft %d · remembered %d / %d years. Larger values are not always better: debt, exposed forces and unused capacity need context." % [int(current.streaks[faction]), int(remembered.streaks[faction]), int(view.game.rules.objective_hold_years)])


func review(box: VBoxContainer) -> void:
	W.clear(box)
	var data: Variant = host.view.desk.review
	if data == null:
		W.text(box, "End the first year to begin the review.")
		return
	W.text(box, "%d resolved · Actual results" % int(data.year))
	W.button(box, "Skip review / return to planning", host.close_review)
	W.text(box, "Instant manual steps in resolution order. Headlines link to their recorded causes. Replaying a review never advances the campaign.")
	for highlight in data.highlights[host.commander]:
		W.prose(box, highlight.message)
		if highlight.phase != null:
			var index: int = host.view.catalog.phases.keys().find(highlight.phase)
			W.button(box, "Inspect cause · " + str(host.view.catalog.phases[highlight.phase]), host.review_step.bind(index))
	if not data.grouped:
		W.text(box, "This older save has an ungrouped chronicle. New years record phase boundaries.")
		W.prose(box, "\n\n".join(host.view.game.reports[-1].messages))
		return
	var step: int = clampi(int(host.ui.review_step), 0, data.phases.size() - 1)
	var phase: Dictionary = data.phases[step]
	W.text(box, "%d / %d · %s" % [step + 1, data.phases.size(), phase.name])
	W.prose(box, "\n\n".join(phase.messages) if not phase.messages.is_empty() else "No recorded developments in this phase.")
	var navigation := W.row(box)
	W.button(navigation, "Previous phase", host.review_step.bind(step - 1)).disabled = step == 0
	W.button(navigation, "Next phase", host.review_step.bind(step + 1)).disabled = step == data.phases.size() - 1
