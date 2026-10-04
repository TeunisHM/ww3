extends "res://tests/smoke.gd"
## Complete desktop workflows through native controls and the real Python worker.

var save_root := ""


func choose(faction: String) -> void:
	for index in range(screen.commander_choice.item_count):
		if screen.commander_choice.get_item_text(index) == faction:
			screen.commander_choice.select(index)
			screen.commander_choice.item_selected.emit(index)
			break
	await settle()


func capture(name: String, window: Window = null) -> void:
	var directory := OS.get_environment("WW3_GODOT_CAPTURE_DIR")
	if directory.is_empty():
		return
	DirAccess.make_dir_recursive_absolute(directory)
	await process_frame
	await RenderingServer.frame_post_draw
	var viewport: Viewport = root if window == null else window
	viewport.get_texture().get_image().save_png(directory.path_join(name + ".png"))


func _run() -> void:
	save_root = OS.get_environment("WW3_GODOT_SAVE_DIR")
	if save_root.is_empty():
		push_error("Set a disposable WW3_GODOT_SAVE_DIR before running feature tests.")
		quit(1)
		return
	screen = load("res://scenes/command.tscn").instantiate()
	root.add_child(screen)
	await settle()
	if failed:
		quit(1)
		return
	screen.intro_dialog.hide()
	screen.close_review()
	screen.handoff_dialog.hide()
	await settle()
	# Configure a fully playable sandbox using the same controls as the player.
	screen.mode_choice.select(2)
	screen.faction_choice.select(0)
	screen.new_dialog.settings.contract_years.value = 2
	screen.new_dialog.settings.government_transition_years.value = 2
	screen.new_dialog.settings.ai_seed.value = 92
	for faction in screen.view.factions:
		screen.new_dialog.assets.starting_capital[faction].value = 300
		screen.new_dialog.assets.starting_minerals[faction].value = 200
		screen.new_dialog.assets.starting_energy[faction].value = 200
	screen.new_dialog.popup_centered_ratio(.85)
	await capture("scenario", screen.new_dialog)
	screen.new_dialog.hide()
	screen.new_dialog.confirmed.emit()
	await settle()
	check(screen.view.game.mode == "sandbox" and int(screen.view.game.rules.ai_seed) == 92, "Scenario controls did not reach the engine")
	check(float(screen.view.game.nations.EU.currency) == 300, "Starting resources were ignored")
	check(screen.investments.size() == 12, "A facility or project editor is missing")
	# Click in reverse order to ensure resolution still follows the displayed catalog.
	var keys: Array = screen.view.catalog.investments.keys()
	keys.reverse()
	for key in keys:
		screen.investments[key].value = 0.5
		await settle()
		check(is_equal_approx(float(screen.view.game.orders.EU.investments.get(key, -1)), 0.5), "Investment editor failed: " + str(key))
	check(screen.view.game.orders.EU.investments.keys() == screen.view.catalog.investments.keys(), "Construction order depends on click order")
	check(screen.view.forecast == null, "A research program cannot spend compute before the first production year")
	screen.investments.research_grant.value = 0
	await settle()
	check(screen.view.forecast != null, "Affordable construction drafts should have a forecast")
	# Every diplomacy action and tariff; matching offers across commanders.
	screen.diplomacy_controls["tariffs/US"].value = 8.5
	await settle()
	for field in ["trade_offers", "alliance_offers", "improve_relations", "foreign_aid"]:
		screen.diplomacy_controls[field + "/US"].button_pressed = true
		await settle()
		check("US" in screen.view.game.orders.EU[field], "Diplomacy control failed: " + field)
	check(is_equal_approx(float(screen.view.game.orders.EU.tariffs.US), .085), "Tariff percentage was converted incorrectly")
	await choose("US")
	for field in ["trade_offers", "alliance_offers", "share_bonus"]:
		screen.diplomacy_controls[field + "/EU"].button_pressed = true
		await settle()
	check("EU" in screen.view.game.orders.US.share_bonus, "National benefit sharing is missing")
	await choose("EU")
	screen.tax.value = 35
	await settle()
	screen.domestic_repayment.value = .25
	await settle()
	screen.government_choice.select(2)
	screen.government_choice.item_selected.emit(2)
	await settle()
	check(screen.view.game.orders.EU.government == "Authoritarian/one-party", "Government selection was ignored")
	for control in screen.contract_controls.values():
		check(not control.editable, "A foreign contract can be edited before maturity")
	# Alternatives remain undoable and compare against the same current rivals.
	screen.show_planning()
	await settle()
	screen.remember_button.pressed.emit()
	await settle()
	screen.planning_dialog.hide()
	screen.tax.value = 30
	await settle()
	screen.show_planning()
	await settle()
	check(not screen.comparison.is_empty(), "Remembered alternatives were not forecast")
	check(screen.comparison.current.forecast != screen.comparison.remembered.forecast, "Comparison reused stale predictions")
	await capture("planning", screen.planning_dialog)
	screen.restore_button.pressed.emit()
	await settle()
	check(is_equal_approx(float(screen.view.game.orders.EU.tax_rate), .35), "Restore alternative failed")
	screen.planning_dialog.hide()
	screen.undo_button.pressed.emit()
	await settle()
	check(is_equal_approx(float(screen.view.game.orders.EU.tax_rate), .30), "Restoring an alternative was not undoable")
	# The visible forecast must equal the completed world's resources.
	var expected: Array = screen.view.forecast.factions.EU.resources.duplicate(true)
	screen.commit_button.pressed.emit()
	await settle()
	check(int(screen.view.game.round) == 2, "Sandbox did not resolve once")
	check("EU|US" in screen.view.game.trades and "EU|US" in screen.view.game.alliances, "Matching treaties were not resolved")
	for row in expected:
		if row.key != "debt":
			check(is_equal_approx(float(row.expected), float(screen.view.game.nations.EU[row.key])), "Full draft forecast mismatch: " + str(row.key))
	check(screen.government_choice.disabled, "An active government transition can be redirected")
	check(screen.review_dialog.visible, "Resolution did not open the review")
	for step in range(6):
		screen.review_step(step)
		await settle()
		check(int(screen.view.game.round) == 2, "Review advanced the campaign")
	await capture("review", screen.review_dialog)
	screen.close_review()
	await settle()
	screen.investments.research_grant.value = .5
	await settle()
	check(screen.view.forecast != null, "Research projects should be available after compute is produced")
	# Partial construction can pause while keeping its paid progress.
	var before_progress: float = screen.view.game.nations.EU.progress.factory
	check(before_progress > 0 and float(screen.view.game.orders.EU.investments.get("factory", 0)) == 0, "Construction did not carry unpaid work correctly")
	# At maturity, both borrowers and lenders get their respective controls.
	var borrower_id := ""
	var lender_id := ""
	for contract in screen.view.game.contracts:
		if contract.borrower == "EU" and borrower_id.is_empty():
			borrower_id = contract.id
		if contract.lender == "EU" and lender_id.is_empty():
			lender_id = contract.id
	check(not borrower_id.is_empty() and not lender_id.is_empty(), "Missing opening foreign debt")
	check(screen.contract_controls[borrower_id].editable and screen.contract_controls[lender_id].editable, "Mature contracts stayed locked")
	var old_principal := 0.0
	for contract in screen.view.game.contracts:
		if contract.id == borrower_id:
			old_principal = float(contract.principal)
	screen.contract_controls[borrower_id].value = .1
	await settle()
	screen.contract_controls[lender_id].value = 7.5
	await settle()
	check(is_equal_approx(float(screen.view.game.orders.EU.foreign_repayments[borrower_id]), .1), "Foreign principal editor failed")
	check(is_equal_approx(float(screen.view.game.orders.EU.contract_rates[lender_id]), .075), "Renewal rate editor failed")
	screen.commit_button.pressed.emit()
	await settle()
	screen.close_review()
	await settle()
	check(screen.view.game.nations.EU.government == "Authoritarian/one-party", "Government transition did not complete")
	check(is_equal_approx(float(screen.view.game.nations.EU.progress.factory), before_progress), "Paused construction progress was lost")
	for contract in screen.view.game.contracts:
		if contract.id == borrower_id:
			check(is_equal_approx(float(contract.principal), old_principal - .1), "Mature foreign repayment did not resolve")
		if contract.id == lender_id:
			check(is_equal_approx(float(contract.rate), .075), "Lender renewal did not resolve")
	# Inspect each command screen, objective shortcut and all history metrics.
	for index in range(8):
		screen.tabs.current_tab = index
		await settle()
		check(screen.page_boxes[index].get_child_count() > 0, "Command page is empty")
		await capture("page-" + str(index))
	screen.inspect_faction = "Russia"
	screen._render()
	screen.inspect_front("Arctic")
	await settle()
	check(screen.tabs.current_tab == 3 and screen.selected_front == "Arctic", "Objective theater shortcut failed")
	for metric in ["gdp", "currency", "debt", "content", "innovation", "military", "influence", "energy", "minerals"]:
		screen.history_metric = metric
		screen._render()
		await process_frame
	check(screen.design_text().contains("Geopolitics") or screen.design_text().contains("WW3"), "Rulebook is unavailable")
	screen.export_design(save_root.path_join("DESIGN.md"))
	check(FileAccess.get_file_as_string(save_root.path_join("DESIGN.md")) == screen.design_text(), "Rulebook export changed the content")
	# Presentation and location survive a restart; portable saves stay untouched.
	screen._render_settings()
	screen.settings_dialog.popup_centered_ratio(.7)
	screen.settings_controls.sound_enabled.button_pressed = true
	await settle()
	screen.settings_controls.sound_volume.value = 20
	await settle()
	screen.settings_controls.text_scale.select(3)
	screen.settings_controls.text_scale.item_selected.emit(3)
	await settle()
	screen.settings_controls.reduce_motion.button_pressed = true
	screen.settings_controls.guide_enabled.button_pressed = false
	await settle()
	await capture("settings", screen.settings_dialog)
	screen.settings_dialog.hide()
	screen.sound.cue("resolve", screen.ui)
	check(screen.resources.get_parent().size.y >= screen.resources.size.y, "Large text clips the planning resource balances")
	await capture("large-text")
	var portable := save_root.path_join("features.json")
	screen.export_to_path(portable)
	await settle()
	var saved_text := FileAccess.get_file_as_string(portable)
	var old_pid: int = screen.bridge.pid
	screen.queue_free()
	await process_frame
	check_worker_stopped(old_pid)
	screen = load("res://scenes/command.tscn").instantiate()
	root.add_child(screen)
	await settle()
	check(int(screen.ui.text_scale) == 150 and screen.ui.sound_enabled and not screen.ui.guide_enabled, "Presentation preferences did not recover")
	check(screen.selected_front == "Arctic" and screen.tabs.current_tab == 3, "Navigation did not recover")
	screen.export_to_path(portable)
	await settle()
	check(FileAccess.get_file_as_string(portable) == saved_text, "Preferences or recovery changed the portable game")
	# Invalid and corrupt imports leave the campaign intact.
	var bad := FileAccess.open(save_root.path_join("broken.json"), FileAccess.WRITE)
	bad.store_string("{broken")
	bad.close()
	screen.import_from_path(save_root.path_join("broken.json"))
	await settle()
	check(int(screen.view.game.round) == 3, "A corrupt import changed the campaign")
	# A completed victory remains playable; open/influence modes are configurable.
	screen.new_dialog.victory_choice.select(2)
	screen.new_dialog.settings.victory_target.value = 150
	screen.new_dialog.confirmed.emit()
	await settle()
	check(screen.view.game.rules.victory_mode == "influence" and int(screen.view.game.rules.victory_target) == 150, "Influence victory setup failed")
	screen.new_dialog.victory_choice.select(1)
	screen.new_dialog.confirmed.emit()
	await settle()
	check(screen.view.game.rules.victory_mode == "open", "Open-ended setup failed")
	# Continue a retained campaign whose winner was actually declared by the engine.
	var winning_save := ProjectSettings.globalize_path("res://../../playtests/replays/EU-military-17/final.json").simplify_path()
	screen.import_from_path(winning_save)
	await settle()
	var won_round := int(screen.view.game.round)
	check(not screen.view.game.winners.is_empty() and not screen.commit_button.disabled, "A won campaign cannot continue")
	screen.commit_button.pressed.emit()
	await settle()
	screen.close_review()
	await settle()
	check(int(screen.view.game.round) == won_round + 1 and not screen.view.game.winners.is_empty(), "Continuing after victory lost the result or failed to advance")
	# Return to the real saved campaign before shutdown.
	screen.import_from_path(portable)
	await settle()
	old_pid = screen.bridge.pid
	screen.queue_free()
	await process_frame
	check_worker_stopped(old_pid)
	if not failed:
		print("Godot feature workflows passed: all investments, diplomacy, government, debt, scenarios, comparison, reviews, history, preferences and saves.")
	quit(1 if failed else 0)
