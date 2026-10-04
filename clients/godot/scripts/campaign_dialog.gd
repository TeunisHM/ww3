extends ConfirmationDialog
## New-campaign controls populated from the Python catalog.

const W = preload("res://scripts/desk_widgets.gd")
signal configured(mode: String, player: String, rules: Dictionary)
var mode_choice: OptionButton
var faction_choice: OptionButton
var victory_choice: OptionButton
var settings: Dictionary = {}
var assets: Dictionary = {}
var catalog: Dictionary
var faction_brief: RichTextLabel


func configure(data: Dictionary) -> void:
	catalog = data
	title = "New campaign"
	ok_button_text = "Take command"
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(760, 520)
	add_child(scroll)
	var box := W.column(scroll)
	W.text(box, "This replaces the active campaign in local recovery. Export a portable save to keep a separate copy.")
	mode_choice = W.choice(box, "Game mode", ["Solo", "Hotseat", "Sandbox"], "Solo")
	faction_choice = W.choice(box, "Starting commander", catalog.scenario.keys(), "EU")
	faction_brief = W.prose(box, "")
	faction_choice.item_selected.connect(func(_index: int): _brief())
	victory_choice = W.choice(box, "Victory rules", ["Faction objectives", "Open-ended simulation", "Total influence target"], "Faction objectives")
	W.text(box, "First year: invest productivity, consider agreements, deploy forces, review policy and objectives, then end the year. All four factions resolve together.")
	var balance := W.section(box, "Scenario & balance settings")
	for key in catalog.scenario_fields:
		var spec: Dictionary = catalog.scenario_fields[key]
		var value := float(catalog.defaults[key]) if key != "victory_target" else 250.0
		settings[key] = W.spin(balance, spec.label, value, float(spec.max), float(spec.step), float(spec.min))
	victory_choice.item_selected.connect(func(index: int): settings.victory_target.editable = index == 2)
	settings.victory_target.editable = false
	for faction in catalog.scenario:
		var section := W.section(box, str(faction) + " starting resources")
		for key in catalog.starting_fields:
			if not assets.has(key):
				assets[key] = {}
			var spec: Dictionary = catalog.starting_fields[key]
			assets[key][faction] = W.spin(section, spec.label, float(catalog.defaults[key][faction]), float(spec.max), 1.0)
	var rows: Array = []
	for faction in catalog.scenario:
		var values: Array = [faction]
		var reserve := float(catalog.scenario[faction].military)
		for power in catalog.defaults.starting_deployments[faction].values():
			values.append(W.number(power, 1))
			reserve -= float(power)
		values.append(W.number(reserve, 1))
		rows.append(values)
	W.table(box, ["Opening deployment", "Europe", "Pacific", "Arctic", "S. America", "Reserve"], rows)
	confirmed.connect(_start)
	_brief()


func _brief() -> void:
	var faction := faction_choice.get_item_text(faction_choice.selected)
	var source: Dictionary = catalog.scenario[faction]
	faction_brief.text = "%s\n%s\nGDP %.2f T · Debt %.2f T · Military %.1f\n%s\nObjective: %s" % [source.name, source.brief, float(source.gdp), float(source.debt), float(source.military), "\n".join(catalog.traits[faction]), catalog.objective_names[faction]]
	for objective in catalog.opening_objectives[faction]:
		faction_brief.text += "\n• " + str(objective.condition)


func _start() -> void:
	var rules := {"victory_mode": ["objectives", "open", "influence"][victory_choice.selected]}
	for key in settings:
		if key == "victory_target" and victory_choice.selected != 2:
			continue
		rules[key] = int(settings[key].value) if catalog.scenario_fields[key].integer else float(settings[key].value)
	for key in assets:
		rules[key] = {}
		for faction in assets[key]:
			rules[key][faction] = float(assets[key][faction].value)
	configured.emit(["solo", "hotseat", "sandbox"][mode_choice.selected], faction_choice.get_item_text(faction_choice.selected), rules)
