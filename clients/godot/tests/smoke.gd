extends SceneTree
## Runs the real scene and Python worker. Use a disposable WW3_GODOT_SAVE_DIR.

var screen: Control
var failed := false


func _initialize() -> void:
	create_timer(120.0).timeout.connect(func(): push_error("Client test exceeded its time limit"); quit(1))
	call_deferred("_run")


func check(condition: bool, message: String) -> void:
	if not condition:
		failed = true
		push_error(message)


func settle() -> void:
	var deadline := Time.get_ticks_msec() + 15000
	await process_frame
	while (screen.bridge.busy or screen._ui_dirty or screen.view.is_empty()) and Time.get_ticks_msec() < deadline:
		await process_frame
	check(not screen.bridge.busy and not screen.view.is_empty(), "Timed out waiting for the Python worker")
	await process_frame


func check_worker_stopped(pid: int) -> void:
	# Godot 4.5 logs ECHILD when is_process_running is called on a child it has
	# already reaped. Inspect its existence from another process instead.
	var python := OS.get_environment("WW3_PYTHON")
	if python.is_empty():
		python = ProjectSettings.globalize_path("res://../../.venv/Scripts/python.exe" if OS.get_name() == "Windows" else "res://../../.venv/bin/python")
	var code := "import os, sys\ntry:\n os.kill(int(sys.argv[1]), 0)\nexcept ProcessLookupError:\n sys.exit(0)\nsys.exit(1)"
	check(OS.execute(python, PackedStringArray(["-c", code, str(pid)])) == 0, "Closing the scene left its Python worker running")


func _run() -> void:
	if OS.get_environment("WW3_GODOT_SAVE_DIR").is_empty():
		push_error("Set WW3_GODOT_SAVE_DIR to a disposable directory before running this test.")
		quit(1)
		return
	screen = load("res://scenes/command.tscn").instantiate()
	root.add_child(screen)
	await settle()
	if failed:
		quit(1)
		return
	screen.intro_dialog.hide()
	screen.bridge.send("new", {"player": "EU", "mode": "solo"})
	await settle()
	check(int(screen.view.game.round) == 1, "New campaign must start in round 1")
	for index in range(4):
		screen.markers[index].pressed.emit()
		check(screen.selected_front == screen.view.fronts[index], "Theater selection failed")
	var precise_tax := 0.321234567890123
	screen.bridge.send("edit", {"faction": "EU", "changes": {"tax_rate": precise_tax}})
	await settle()
	check(float(screen.view.game.orders.EU.tax_rate) == precise_tax, "The bridge rounded a floating-point value")
	screen.factory.value = 5.0
	await settle()
	check(float(screen.view.game.orders.EU.investments.factory) == 5.0, "Factory control did not reach the shared session")
	check(float(screen.view.game.orders.EU.tax_rate) == precise_tax, "Editing construction changed an unrelated order")
	screen.tax.value = 35.0
	await settle()
	check(is_equal_approx(float(screen.view.game.orders.EU.tax_rate), 0.35), "Tax control did not reach the shared session")
	screen.deployments["Eastern Europe"].value = 30.0
	await settle()
	var expected: Array = screen.view.forecast.factions.EU.resources.duplicate(true)
	screen.commit_button.pressed.emit()
	await settle()
	check(int(screen.view.game.round) == 2, "End year must advance exactly once")
	screen.close_review()
	await settle()
	for row in expected:
		if row.key != "debt":
			check(is_equal_approx(float(row.expected), float(screen.view.game.nations.EU[row.key])), "Forecast differed from resolution for " + str(row.key))
	check(is_equal_approx(float(screen.view.game.nations.EU.progress.factory), 0.5), "Partial construction was lost")
	var path := OS.get_environment("WW3_GODOT_SAVE_DIR").path_join("portable.json")
	screen.export_to_path(path)
	await settle()
	check(FileAccess.file_exists(path), "Portable save export failed")
	var saved_text := FileAccess.get_file_as_string(path)
	screen.commit_button.pressed.emit()
	await settle()
	check(int(screen.view.game.round) == 3, "Second year did not advance")
	screen.close_review()
	await settle()
	screen.import_from_path(path)
	await settle()
	check(int(screen.view.game.round) == 2, "Portable import did not restore the saved year")
	var old_pid: int = screen.bridge.pid
	screen.queue_free()
	await process_frame
	check_worker_stopped(old_pid)
	screen = load("res://scenes/command.tscn").instantiate()
	root.add_child(screen)
	await settle()
	check(int(screen.view.game.round) == 2, "Restart did not recover the saved campaign")
	screen.export_to_path(path)
	await settle()
	check(FileAccess.get_file_as_string(path) == saved_text, "Recovery changed the portable save")
	# An invalid combined draft must clear the forecast and block End year.
	var military: float = screen.view.game.nations.EU.military
	screen.deployments["Eastern Europe"].value = military
	await settle()
	screen.deployments["Arctic"].value = military
	await settle()
	check(screen.view.forecast == null and screen.commit_button.disabled, "Invalid orders did not block resolution")
	screen.undo_button.pressed.emit()
	await settle()
	screen.reset_button.pressed.emit()
	await settle()
	check(screen.view.forecast != null, "Reset did not restore a valid forecast")
	screen.mode_choice.select(1)
	screen.faction_choice.select(2)
	screen.new_dialog.confirmed.emit()
	await settle()
	check(screen.view.game.mode == "hotseat" and screen.commander == "China", "New campaign ignored its selected mode or commander")
	for index in range(4):
		var committed_faction: String = screen.commander
		screen.commit_button.pressed.emit()
		await settle()
		check(int(screen.view.game.round) == (2 if index == 3 else 1), "Hotseat must resolve only after four submissions")
		screen._accept_handoff()
		screen.close_review()
		await settle()
		if index == 0:
			for option in range(screen.commander_choice.item_count):
				if screen.commander_choice.get_item_text(option) == committed_faction:
					screen.commander_choice.select(option)
					screen.commander_choice.item_selected.emit(option)
					break
			await settle()
			check(not screen.factory.editable and screen.government_choice.disabled and screen.commit_button.disabled, "Committed hotseat orders are editable")
			screen.reopen_button.pressed.emit()
			await settle()
			check(screen.factory.editable and screen.view.game.submitted.is_empty(), "Reopening did not unlock orders")
			screen.commit_button.pressed.emit()
			await settle()
			screen._accept_handoff()
			await settle()
	screen.import_from_path(path)
	await settle()
	# Optional rendering capture when run with a display instead of --headless.
	var capture := OS.get_environment("WW3_GODOT_CAPTURE")
	if not capture.is_empty():
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(capture)
	old_pid = screen.bridge.pid
	screen.queue_free()
	await process_frame
	check_worker_stopped(old_pid)
	if not failed:
		print("Godot smoke passed: controls, forecasts, resolution, save/import, restart, invalid drafts, and worker shutdown.")
	quit(1 if failed else 0)
