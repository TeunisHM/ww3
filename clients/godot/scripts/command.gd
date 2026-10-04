extends Control
## Desktop campaign controller. Python owns every rule and turn transition.

const Bridge = preload("res://scripts/local_bridge.gd")
const W = preload("res://scripts/desk_widgets.gd")
const Pages = preload("res://scripts/desk_pages.gd")
const CampaignDialog = preload("res://scripts/campaign_dialog.gd")
const Sound = preload("res://scripts/sound_cues.gd")

var bridge: Node
var pages: RefCounted
var sound: Node
var view: Dictionary = {}
var ui: Dictionary = {}
var commander := "EU"
var selected_front := "Eastern Europe"
var _updating := false
var _fatal := false
var _ui_dirty := false
var _pending_export := ""
var _export_design := false
var comparison: Dictionary = {}
var inspect_faction := "EU"
var history_metric := "gdp"
var history_report := -1
var folds: Dictionary = {}
var controls: Dictionary = {}
var edit_controls: Array[Control] = []
var action_buttons: Array[Button] = []
var page_boxes: Array[VBoxContainer] = []
var page_scrolls: Array[ScrollContainer] = []
var markers: Array[Button] = []
var deployments: Dictionary = {}
var investments: Dictionary = {}
var diplomacy_controls: Dictionary = {}
var contract_controls: Dictionary = {}
var settings_controls: Dictionary = {}
var factory: SpinBox
var tax: SpinBox
var government_choice: OptionButton
var domestic_repayment: SpinBox
var title: Label
var status: Label
var outlook: Label
var draft_summary: Label
var resources: HBoxContainer
var tabs: TabContainer
var commander_choice: OptionButton
var mode_choice: OptionButton
var faction_choice: OptionButton
var commit_button: Button
var undo_button: Button
var reset_button: Button
var reopen_button: Button
var save_dialog: FileDialog
var load_dialog: FileDialog
var new_dialog: ConfirmationDialog
var planning_dialog: AcceptDialog
var planning_box: VBoxContainer
var review_dialog: AcceptDialog
var review_box: VBoxContainer
var handoff_dialog: AcceptDialog
var intro_dialog: AcceptDialog
var settings_dialog: AcceptDialog
var settings_box: VBoxContainer
var front_detail: RichTextLabel
var report: RichTextLabel
var remember_button: Button
var restore_button: Button
var compare_button: Button


func _ready() -> void:
	_build_ui()
	pages = Pages.new(self)
	sound = Sound.new()
	add_child(sound)
	bridge = Bridge.new()
	add_child(bridge)
	bridge.replied.connect(_on_reply)
	bridge.failed.connect(_on_failure)
	bridge.busy_changed.connect(_set_busy)
	if bridge.start():
		bridge.send("state")


func _process(_delta: float) -> void:
	if _ui_dirty and not _fatal and bridge != null and not bridge.busy:
		_ui_dirty = false
		bridge.send("ui", {"values": ui})


func _action(parent: Node, caption: String, callback: Callable) -> Button:
	var control := W.button(parent, caption, callback)
	action_buttons.append(control)
	return control


func _dialog(caption: String, minimum := Vector2(760, 480)) -> AcceptDialog:
	var dialog := AcceptDialog.new()
	dialog.title = caption
	dialog.ok_button_text = "Return to planning"
	dialog.set_meta("minimum", minimum)
	add_child(dialog)
	return dialog


func _dialog_box(dialog: AcceptDialog) -> VBoxContainer:
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = dialog.get_meta("minimum")
	dialog.add_child(scroll)
	return W.column(scroll)


func _build_ui() -> void:
	theme = Theme.new()
	theme.default_font_size = 16
	theme.set_color("font_color", "Label", Color("dce8ef"))
	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 14)
	add_child(margin)
	var column := W.column(margin)
	var heading := W.row(column)
	title = W.text(heading, "WW3 · Opening command desk…")
	commander_choice = OptionButton.new()
	commander_choice.item_selected.connect(_commander_changed)
	heading.add_child(commander_choice)
	var toolbar := HFlowContainer.new()
	column.add_child(toolbar)
	_action(toolbar, "New campaign", func(): new_dialog.popup_centered_ratio(0.85))
	_action(toolbar, "Export save", func(): _export_design = false; save_dialog.current_file = "ww3-campaign.json"; save_dialog.popup_centered_ratio(0.75))
	_action(toolbar, "Import save", func(): load_dialog.popup_centered_ratio(0.75))
	_action(toolbar, "Reload latest", func(): bridge.send("recover"))
	_action(toolbar, "Recover previous", func(): bridge.send("recover", {"previous": true}))
	_action(toolbar, "Briefing", func(): intro_dialog.popup_centered_ratio(0.8))
	_action(toolbar, "Settings", func(): _render_settings(); settings_dialog.popup_centered_ratio(0.7))
	var resource_scroll := ScrollContainer.new()
	resource_scroll.custom_minimum_size.y = 64
	resource_scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	column.add_child(resource_scroll)
	resources = W.row(resource_scroll)
	resources.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	for index in range(7):
		var label := W.text(resources, "—")
		label.custom_minimum_size.x = 142
		label.autowrap_mode = TextServer.AUTOWRAP_OFF
	draft_summary = W.text(column, "")
	var actions := HFlowContainer.new()
	column.add_child(actions)
	undo_button = _action(actions, "Undo edit", func(): _draft_command("undo"))
	reset_button = _action(actions, "Reset draft", func(): _draft_command("reset"))
	_action(actions, "Ledger & alternatives", show_planning)
	_action(actions, "Review last year", show_review)
	reopen_button = _action(actions, "Reopen orders", func(): _draft_command("reopen"))
	commit_button = _action(actions, "End year", func(): _draft_command("commit"))
	status = W.text(column, "Connecting to the simulation…")
	outlook = W.text(column, "")
	tabs = TabContainer.new()
	tabs.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(tabs)
	for caption in ["Situation", "Economy", "Diplomacy", "Military", "Government", "Objectives", "Chronicle", "Rules"]:
		var scroll := ScrollContainer.new()
		scroll.name = caption
		scroll.follow_focus = true
		tabs.add_child(scroll)
		page_scrolls.append(scroll)
		page_boxes.append(W.column(scroll))
	tabs.tab_changed.connect(_page_changed)
	save_dialog = FileDialog.new()
	save_dialog.access = FileDialog.ACCESS_FILESYSTEM
	save_dialog.file_mode = FileDialog.FILE_MODE_SAVE_FILE
	save_dialog.filters = PackedStringArray(["*.json ; WW3 campaign", "*.md ; Game design"])
	save_dialog.file_selected.connect(func(path: String): export_design(path) if _export_design else export_to_path(path))
	add_child(save_dialog)
	load_dialog = FileDialog.new()
	load_dialog.access = FileDialog.ACCESS_FILESYSTEM
	load_dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
	load_dialog.filters = PackedStringArray(["*.json ; WW3 campaign"])
	load_dialog.file_selected.connect(import_from_path)
	add_child(load_dialog)
	planning_dialog = _dialog("Planning ledger & draft alternatives")
	planning_box = _dialog_box(planning_dialog)
	review_dialog = _dialog("Turn review")
	review_box = _dialog_box(review_dialog)
	review_dialog.confirmed.connect(close_review)
	review_dialog.canceled.connect(close_review)
	handoff_dialog = _dialog("Pass command", Vector2(600, 180))
	handoff_dialog.ok_button_text = "Open command desk"
	handoff_dialog.exclusive = true
	handoff_dialog.confirmed.connect(_accept_handoff)
	handoff_dialog.canceled.connect(_accept_handoff)
	intro_dialog = _dialog("Power has a price")
	var intro := _dialog_box(intro_dialog)
	W.prose(intro, "POWER HAS A PRICE\n\nFour powers compete across Eastern Europe, the Pacific, the Arctic and South America. Build the economy that supports your ambitions: energy powers industry, minerals build it, compute advances it, and productivity turns plans into facilities. Treasury pays the bills; debt keeps charging interest.\n\nTrade can share national advantages. Alliances combine armies whose objectives may differ. Military share measures the forces present; territorial influence survives withdrawal. In the default campaign, meet every national objective for three consecutive completed years.\n\nPlan construction, consider agreements, deploy forces and review policy. The ledger previews the exact consequences of this year's orders. Unused compute and productivity expire. Partial construction carries forward. Nothing advances until you end the year.")
	W.button(intro, "Start a new EU solo campaign", func(): intro_dialog.hide(); bridge.send("new", {"mode": "solo", "player": "EU"}))
	W.button(intro, "Choose faction, mode & scenario", func(): intro_dialog.hide(); new_dialog.popup_centered_ratio(0.85))
	W.button(intro, "Import a campaign", func(): intro_dialog.hide(); load_dialog.popup_centered_ratio(0.75))
	W.text(intro, "Starting a new campaign replaces the local recovery slot. Export a save first to keep another campaign.")
	settings_dialog = _dialog("Sound, display & guidance", Vector2(640, 320))
	settings_box = _dialog_box(settings_dialog)
	_set_busy(true)


func register_edit(control: Control, id: String, eligible: bool = true) -> void:
	control.set_meta("eligible", eligible)
	control.set_meta("control_id", id)
	if control is SpinBox:
		control.get_line_edit().set_meta("control_id", id)
	controls[id] = control
	edit_controls.append(control)


func _set_busy(value: bool) -> void:
	var locked: bool = _fatal or value or view.is_empty()
	for button in action_buttons:
		button.disabled = locked
	commander_choice.disabled = locked
	if view.is_empty():
		return
	var submitted: bool = commander in view.game.submitted
	for control in edit_controls:
		var enabled: bool = not locked and not submitted and control.get_meta("eligible", true)
		if control is SpinBox:
			control.editable = enabled
		else:
			control.disabled = not enabled
	undo_button.disabled = locked or not view.can_undo[commander]
	reset_button.disabled = locked or submitted
	reopen_button.visible = submitted
	var resolves: bool = view.game.mode != "hotseat" or view.game.submitted.size() == 3
	commit_button.disabled = locked or submitted or view.desk.factions[commander].plan_error != null or (resolves and view.forecast == null)
	if is_instance_valid(remember_button):
		remember_button.disabled = locked or submitted
		restore_button.disabled = locked or not view.can_restore[commander]
		compare_button.disabled = locked or not view.can_restore[commander]


func _on_reply(message: Dictionary) -> void:
	if not message.ok:
		status.text = str(message.error.message)
		sound.cue("warning", ui)
		return
	var result: Dictionary = message.result
	if result.has("save"):
		_write_file(_pending_export, result.save)
		_pending_export = ""
		return
	if bridge.last_command == "ui":
		view.checkpoint_error = result.checkpoint_error
		if result.checkpoint_error != null:
			status.text = "Changes are not saved: " + str(result.checkpoint_error) + " Export a portable copy."
		return
	if bridge.last_command == "compare":
		comparison = result
		pages.planning(planning_box)
		_set_busy(false)
		return
	if not result.has("game"):
		return
	var first := view.is_empty()
	var changed_campaign: bool = first or bridge.last_command in ["new", "load", "recover"]
	view = result
	comparison = {}
	if changed_campaign or result.has("turn"):
		ui = result.ui.duplicate(true)
		for key in ["sound_volume", "text_scale", "review_step"]:
			ui[key] = int(ui[key])
		_ui_dirty = false
		commander = ui.commander
		selected_front = ui.selected_front
		inspect_faction = commander
		history_report = -1
	if view.game.mode == "solo":
		commander = view.game.player
	if first:
		new_dialog = CampaignDialog.new()
		add_child(new_dialog)
		new_dialog.configure(view.catalog)
		new_dialog.configured.connect(func(mode: String, player: String, rules: Dictionary): bridge.send("new", {"mode": mode, "player": player, "rules": rules}))
		mode_choice = new_dialog.mode_choice
		faction_choice = new_dialog.faction_choice
	if changed_campaign:
		_apply_display()
		_updating = true
		tabs.current_tab = maxi(0, view.catalog.pages.find(ui.page))
		_updating = false
	_render()
	if result.has("turn"):
		sound.cue("victory" if result.turn.new_victory else "resolve" if result.turn.resolved else "commit", ui)
	elif bridge.last_command in ["edit", "undo", "reset", "restore"]:
		sound.cue("warning" if view.forecast == null else "order", ui)
	if ui.handoff:
		handoff_dialog.dialog_text = "Pass command to %s.\n%d of 4 factions have committed for %d.\nAll information is shared; the world advances after all four submissions." % [commander, view.game.submitted.size(), int(view.year)]
		handoff_dialog.popup_centered(Vector2i(660, 230))
	elif ui.review_open and view.desk.review != null and (changed_campaign or result.has("turn")):
		show_review(false)
	if first and view.first_launch:
		intro_dialog.popup_centered_ratio(0.8)
	if planning_dialog.visible and view.can_restore[commander] and not bridge.busy:
		_draft_command("compare")


func _render() -> void:
	_updating = true
	var focus_id := ""
	var focused := get_viewport().gui_get_focus_owner()
	if focused != null:
		focus_id = str(focused.get_meta("control_id", ""))
	var scroll_positions: Array = []
	for scroll in page_scrolls:
		scroll_positions.append(scroll.scroll_vertical)
	edit_controls.clear()
	controls.clear()
	markers.clear()
	deployments.clear()
	investments.clear()
	diplomacy_controls.clear()
	contract_controls.clear()
	var game: Dictionary = view.game
	var facts: Dictionary = view.desk.factions[commander]
	title.text = "WW3  ·  %s  ·  %s  ·  %d (round %d)" % [commander, game.mode.capitalize(), int(view.year), int(game.round)]
	commander_choice.clear()
	for faction in view.factions:
		if game.mode != "solo" or faction == game.player:
			commander_choice.add_item(faction)
			if faction == commander:
				commander_choice.select(commander_choice.item_count - 1)
	var names := ["currency", "energy", "minerals", "compute", "productivity", "innovation", "military"]
	var labels := ["Treasury · T", "Energy · PJ", "Minerals · t", "Compute ↻", "Productivity ↻", "Innovation", "Military"]
	for index in range(names.size()):
		var expected: Variant = null
		if view.forecast != null:
			for row in view.forecast.factions[commander].resources:
				if row.key == names[index]:
					expected = row.expected
		resources.get_child(index).text = "%s\n%s → %s" % [labels[index], W.number(game.nations[commander][names[index]]), W.number(expected)]
	draft_summary.text = "%.1f productivity remaining · %.1f planned reserve · %d changed decisions · %s" % [float(facts.remaining_productivity), float(facts.reserve), facts.changes.size(), " | ".join(_order_status())]
	commit_button.text = "Commit & pass" if game.mode == "hotseat" and game.submitted.size() < 3 else "End year · resolve all"
	status.text = "Draft saved locally. Forecast includes computer responses." if game.mode == "solo" else "Draft saved locally. Forecast depends on every faction's current draft."
	if view.forecast_error != null:
		status.text = "Forecast unavailable: " + str(view.forecast_error)
	if not str(view.notice).is_empty():
		status.text += " " + str(view.notice)
	if view.checkpoint_error != null:
		status.text += " Changes are not saved: " + str(view.checkpoint_error) + " Export a portable copy."
	outlook.text = pages.outlook()
	for index in range(page_boxes.size()):
		W.clear(page_boxes[index])
		pages.build(index, page_boxes[index])
	if planning_dialog.visible:
		pages.planning(planning_box)
	if review_dialog.visible:
		pages.review(review_box)
	_updating = false
	_set_busy(bridge.busy)
	_restore_position.call_deferred(scroll_positions, focus_id)


func _restore_position(positions: Array, focus_id: String) -> void:
	if controls.has(focus_id):
		var control: Control = controls[focus_id]
		if control is SpinBox:
			control.get_line_edit().grab_focus()
		else:
			control.grab_focus()
	for index in range(page_scrolls.size()):
		page_scrolls[index].set_deferred("scroll_vertical", positions[index])


func _order_status() -> PackedStringArray:
	var states := PackedStringArray()
	for faction in view.factions:
		states.append(str(faction) + ": " + ("committed" if faction in view.game.submitted else "AI" if view.game.mode == "solo" and faction != view.game.player else "planning"))
	return states


func _draft_command(command: String) -> void:
	if not _fatal and not bridge.busy:
		bridge.send(command, {"faction": commander})


func _order_changed(value: float, field: String, key: String = "", scale: float = 1.0) -> void:
	if _updating or view.is_empty() or bridge.busy:
		return
	var changes := {}
	value /= scale
	if key.is_empty():
		changes[field] = value
	else:
		var values: Dictionary = view.game.orders[commander][field].duplicate(true)
		if field == "investments" and value == 0:
			values.erase(key)
		else:
			values[key] = value
		if field == "investments":
			var ordered := {}
			for investment in view.catalog.investments:
				if values.has(investment):
					ordered[investment] = values[investment]
			values = ordered
		changes[field] = values
	bridge.send("edit", {"faction": commander, "changes": changes})


func _list_changed(enabled: bool, field: String, other: String) -> void:
	if _updating or bridge.busy:
		return
	var values: Array = view.game.orders[commander][field].duplicate()
	values.erase(other)
	if enabled:
		values.append(other)
	bridge.send("edit", {"faction": commander, "changes": {field: values}})


func _government_changed(index: int) -> void:
	if not _updating and not bridge.busy:
		bridge.send("edit", {"faction": commander, "changes": {"government": view.catalog.governments[index]}})


func _select_front(index: int) -> void:
	if view.is_empty():
		return
	selected_front = view.fronts[index]
	set_ui("selected_front", selected_front)
	_render()


func inspect_front(front: String) -> void:
	selected_front = front
	set_ui("selected_front", front)
	tabs.current_tab = 3
	_render()


func _commander_changed(index: int) -> void:
	if _updating:
		return
	commander = commander_choice.get_item_text(index)
	inspect_faction = commander
	comparison = {}
	set_ui("commander", commander)
	_render()


func _page_changed(index: int) -> void:
	if not _updating and not view.is_empty():
		set_ui("page", view.catalog.pages[index])


func set_ui(key: String, value: Variant) -> void:
	ui[key] = value
	_ui_dirty = true


func show_planning() -> void:
	pages.planning(planning_box)
	planning_dialog.popup_centered_ratio(0.85)
	_set_busy(bridge.busy)
	if view.can_restore[commander] and not bridge.busy:
		_draft_command("compare")


func show_review(reset_step: bool = true) -> void:
	if view.desk.review == null:
		status.text = "End the first year to begin the turn review."
		return
	set_ui("review_open", true)
	if reset_step:
		set_ui("review_step", 0)
	pages.review(review_box)
	review_dialog.popup_centered_ratio(0.85)


func review_step(step: int) -> void:
	set_ui("review_step", clampi(step, 0, 5))
	pages.review(review_box)


func close_review() -> void:
	set_ui("review_open", false)
	review_dialog.hide()


func _accept_handoff() -> void:
	set_ui("handoff", false)
	handoff_dialog.hide()
	if ui.review_open:
		show_review(false)


func _apply_display() -> void:
	theme.default_font_size = roundi(16.0 * float(ui.text_scale) / 100.0)
	resources.get_parent().custom_minimum_size.y = theme.default_font_size * 3 + 24


func _render_settings() -> void:
	W.clear(settings_box)
	settings_controls.clear()
	var enabled := CheckBox.new()
	enabled.text = "Enable sound effects (muted by default)"
	enabled.button_pressed = ui.sound_enabled
	settings_box.add_child(enabled)
	settings_controls.sound_enabled = enabled
	enabled.toggled.connect(func(value: bool): set_ui("sound_enabled", value); sound.cue("order", ui))
	var volume := W.spin(settings_box, "Sound volume · %", float(ui.sound_volume), 100)
	settings_controls.sound_volume = volume
	volume.value_changed.connect(func(value: float): set_ui("sound_volume", int(value)))
	W.button(settings_box, "Test sound", func(): sound.cue("resolve", ui))
	var scale := W.choice(settings_box, "Text size · %", [100, 115, 130, 150], str(int(ui.text_scale)))
	settings_controls.text_scale = scale
	scale.item_selected.connect(func(index: int): set_ui("text_scale", [100, 115, 130, 150][index]); _apply_display(); _render())
	var motion := CheckBox.new()
	motion.text = "Reduce motion"
	motion.button_pressed = ui.reduce_motion
	settings_box.add_child(motion)
	settings_controls.reduce_motion = motion
	motion.toggled.connect(func(value: bool): set_ui("reduce_motion", value))
	W.text(settings_box, "Turn reviews use instant, manual steps. No animation is required to play.")
	var guide := CheckBox.new()
	guide.text = "Show first-three-year guidance"
	guide.button_pressed = ui.guide_enabled
	settings_box.add_child(guide)
	settings_controls.guide_enabled = guide
	guide.toggled.connect(func(value: bool): set_ui("guide_enabled", value); _render())
	W.text(settings_box, "Preferences stay in local recovery and are separate from portable campaign saves.")


func export_to_path(path: String) -> void:
	if bridge.busy:
		status.text = "Wait for the current command to finish, then export again."
		return
	_pending_export = path
	bridge.send("export")


func _write_file(path: String, content: String) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		status.text = "Could not export: " + error_string(FileAccess.get_open_error())
		return
	file.store_string(content)
	file.flush()
	status.text = "Exported to " + path if file.get_error() == OK else "Export could not be completed."
	file.close()


func design_text() -> String:
	var path := ProjectSettings.globalize_path("res://../../DESIGN.md").simplify_path()
	return FileAccess.get_file_as_string(path) if FileAccess.file_exists(path) else "DESIGN.md was not found. Run this development client from the repository. Current campaign settings are listed below."


func export_design(path: String) -> void:
	_write_file(path, design_text())


func import_from_path(path: String) -> void:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		status.text = "Could not open this campaign."
		return
	if file.get_length() > 2000000:
		status.text = "Campaign saves must be smaller than 2 MB."
		file.close()
		return
	var save := file.get_as_text()
	file.close()
	if not bridge.send("load", {"save": save}):
		status.text = "Wait for the current command to finish, then import again."


func _on_failure(message: String) -> void:
	_fatal = true
	status.text = message
	_set_busy(true)
